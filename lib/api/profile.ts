
// ############################################################################
// AI_HEADER: FRONTEND_API_PROFILE — credentialed canonical profile read and update client.
// ROLE: Credentialed profile read and update facade used by profile and onboarding hooks.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-PROFILE
// purpose: GET or PUT the canonical profile and preserve backend error detail.
// owns:
//   - lib/api/profile.ts
// inputs: no arguments for get; ProfileWrite for update; NEXT_PUBLIC_API_URL.
// outputs: exported profile types and Promise<ProfileRead>.
// dependencies: packages/contracts profile types; fetch; JSON.
// side_effects: credentialed GET and PUT /api/profile.
// emitted_logs: none.
// invariants:
//   - Update remains PUT with a JSON body.
//   - Successful response data is returned without local shape rewriting.
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
//   - PROFILE_READ: fetch and return the canonical profile.
//   - PROFILE_UPDATE: PUT profile data and return the canonical result.
// owned_tests:
//   - __tests__/hooks/useProfile.test.ts
//   - __tests__/components/OnboardingFlow.test.tsx
//   - __tests__/components/OnboardingWelcome.test.tsx
// END_MODULE_MAP: M-FRONTEND-API-PROFILE

import type { BirthData, ProfileRead, ProfileWrite } from '@/packages/contracts'
export type { BirthData, ProfileRead, ProfileWrite }

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

async function responseError(res: Response, fallback: string): Promise<Error> {
  const payload = await res.json().catch(() => null)
  const detail = payload?.detail
  if (typeof detail === 'string') return new Error(detail)
  if (detail && typeof detail.message === 'string') return new Error(detail.message)
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter((message): message is string => typeof message === 'string')
    if (messages.length > 0) return new Error(messages.join('. '))
  }
  return new Error(fallback)
}

/**
 * Get user profile
 * @returns ProfileRead
 * @throws Error on HTTP errors
 */
export async function getProfile(): Promise<ProfileRead> {
  const res = await fetch(`${API_BASE}/api/profile`, {
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  })

  if (!res.ok) {
    throw await responseError(res, 'Failed to get profile')
  }

  return res.json()
}

/**
 * Update user profile (partial update)
 * @param data - ProfileWrite with fields to update
 * @returns ProfileRead with updated profile
 * @throws Error on HTTP errors
 */
export async function updateProfile(data: ProfileWrite): Promise<ProfileRead> {
  const res = await fetch(`${API_BASE}/api/profile`, {
    method: 'PUT',
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(data),
  })

  if (!res.ok) {
    throw await responseError(res, 'Failed to update profile')
  }

  return res.json()
}
