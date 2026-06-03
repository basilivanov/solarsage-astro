// AI_HEADER
// module: M-WEB-API-PROFILE
// wave: W-2.7
// purpose: API client for profile endpoints

import type { components } from '@/packages/contracts/_generated'
import { IS_DEMO_MODE } from '@/lib/demo-mode'
import { DEMO_PROFILE } from '@/lib/demo-data'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || ''

// Use types from generated contracts (INV-CONTRACTS-NO-LOCAL-TYPES)
export type BirthData = components['schemas']['BirthData']
export type ProfileRead = components['schemas']['ProfileRead']
export type ProfileWrite = components['schemas']['ProfileWrite']

/**
 * Get user profile
 * @returns ProfileRead
 * @throws Error on HTTP errors
 */
export async function getProfile(): Promise<ProfileRead> {
  if (IS_DEMO_MODE) return DEMO_PROFILE as unknown as ProfileRead;

  const res = await fetch(`${API_BASE}/api/profile`, {
    credentials: 'include',
    headers: {
      'Accept': 'application/json',
    },
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Failed to get profile' }))
    throw new Error(error.detail?.message || error.detail || 'Failed to get profile')
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
    const error = await res.json().catch(() => ({ detail: 'Failed to update profile' }))
    throw new Error(error.detail?.message || error.detail || 'Failed to update profile')
  }

  return res.json()
}
