import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getProfileMeta } from '../../lib/api/profile-meta'

describe('getProfileMeta', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns default values when both calls fail', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

    const result = await getProfileMeta()
    expect(result.horary.left).toBe(0)
    expect(result.referral.count).toBe(0)
    expect(result.referral.inviteUrl).toBe('')
  })

  it('returns quota data on success', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ left: 5, next_in_days: 5 }),
      })
      .mockResolvedValueOnce({
        ok: false,
      })

    const result = await getProfileMeta()
    expect(result.horary.left).toBe(5)
    expect(result.referral.count).toBe(0)
  })

  it('handles quota with missing resetAt', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ left: 3, next_in_days: 7 }),
      })
      .mockResolvedValueOnce({
        ok: false,
      })

    const result = await getProfileMeta()
    expect(result.horary.left).toBe(3)
    expect(result.horary.nextInDays).toBe(7)
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
    expect(result.horary.left).toBe(0)
    expect(result.referral.count).toBe(3)
    expect(result.referral.inviteUrl).toBe('https://t.me/bot?start=ref123')
    expect(result.referral.bonusDays).toBe(42)
  })

  it('returns both when both endpoints succeed', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ left: 2, next_in_days: 7 }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ totalInvited: 1, inviteUrl: 'url' }),
      })

    const result = await getProfileMeta()
    expect(result.horary.left).toBe(2)
    expect(result.referral.count).toBe(1)
  })
})
