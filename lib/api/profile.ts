
// ############################################################################
// AI_HEADER: MODULE_API_PROFILE
// ROLE: Lib — profile.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ####// START_MODULE_CONTRACT
// purpose: API client for profile
// owns:
//   - lib/api/profile.ts
// inputs: Endpoint params, request body
// outputs: Parsed response / typed data
// dependencies: local modules
// side_effects: Network calls to API
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT// AI_HEADER
// module: M-WEB-API-PROFILE
// wave: W-2.7
// purpose: API client for profile endpoints

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
