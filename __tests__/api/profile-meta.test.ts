
// ############################################################################
// AI_HEADER: MODULE_API_PROFILE_META_TEST
// ROLE: Unit tests for profile-meta.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for profile-meta.test.ts — __tests__/api/profile-meta.test.ts
// owns:
//   - __tests__/api/profile-meta.test.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getProfileMeta } from '../../lib/api/profile-meta'

describe('getProfileMeta', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns default values when both calls fail', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

    const result = await getProfileMeta()
    expect(result.horary.weeklyFreeAvailable).toBe(false)
    expect(result.horary.bonusCredits).toBe(0)
    expect(result.horary.paidCredits).toBe(0)
    expect(result.referral.count).toBe(0)
    expect(result.referral.inviteUrl).toBe('')
  })

  it('returns quota data on success', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          weeklyFreeAvailable: true,
          weeklyFreeExpiresAt: '2026-12-31T00:00:00Z',
          bonusCredits: 2,
          paidCredits: 3,
        }),
      })
      .mockResolvedValueOnce({
        ok: false,
      })

    const result = await getProfileMeta()
    expect(result.horary.weeklyFreeAvailable).toBe(true)
    expect(result.horary.weeklyFreeExpiresAt).toBe('2026-12-31T00:00:00Z')
    expect(result.horary.bonusCredits).toBe(2)
    expect(result.horary.paidCredits).toBe(3)
    expect(result.referral.count).toBe(0)
  })

  it('handles quota with missing optional fields', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          weeklyFreeAvailable: false,
          bonusCredits: 1,
          paidCredits: 0,
        }),
      })
      .mockResolvedValueOnce({
        ok: false,
      })

    const result = await getProfileMeta()
    expect(result.horary.weeklyFreeAvailable).toBe(false)
    expect(result.horary.bonusCredits).toBe(1)
    expect(result.horary.paidCredits).toBe(0)
    expect(result.horary.weeklyFreeExpiresAt).toBeNull()
  })

  it('returns referral data on success', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: false,
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ totalInvited: 3, inviteUrl: 'https://t.me/bot?start=ref123' }),
      })

    const result = await getProfileMeta()
    expect(result.horary.weeklyFreeAvailable).toBe(false)
    expect(result.referral.count).toBe(3)
    expect(result.referral.inviteUrl).toBe('https://t.me/bot?start=ref123')
    expect(result.referral.bonusDays).toBe(42)
  })

  it('returns both when both endpoints succeed', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          weeklyFreeAvailable: true,
          bonusCredits: 0,
          paidCredits: 2,
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ totalInvited: 1, inviteUrl: 'url' }),
      })

    const result = await getProfileMeta()
    expect(result.horary.weeklyFreeAvailable).toBe(true)
    expect(result.horary.paidCredits).toBe(2)
    expect(result.referral.count).toBe(1)
  })
})
