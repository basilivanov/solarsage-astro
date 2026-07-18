// ############################################################################
// AI_HEADER: TEST_USE_SHARE_INVITE — share default copy and invite URL contract
// ROLE: Proves the accepted share default text, honest 14-days-both motivator,
//       tone rules, and the working API inviteUrl form.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-USE-SHARE-INVITE
// purpose: Verify the share default is the accepted variant-1 copy with the
//   honest "оба получим по 14 дней" motivator, «гороскоп» appears only with
//   negation (or not at all), and the invite URL keeps the working
//   t.me/vi_astro_bot/app?startapp= form.
// owns:
//   - __tests__/hooks/use-share-invite.test.ts
// inputs: SHARE_TEXT export and useShareInvite hook
// outputs: vitest assertions
// dependencies: vitest
// side_effects: none
// emitted_logs: none
// invariants:
//   - exact accepted copy present; motivator present; no «гороскоп» w/o negation;
//     invite URL keeps startapp form (no ?start=ref_ change)
//   - the bonus motivator is shared only with an attributed link (API
//     inviteUrl or canonical startapp fallback from initDataUnsafe user.id);
//     without a user id the generic /app link is shared with the
//     promise-free generic text
// failure_policy: assertion failure on contract violation
// END_MODULE_CONTRACT: M-TEST-USE-SHARE-INVITE

import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { act, renderHook, waitFor } from '@testing-library/react'
import { SHARE_TEXT, SHARE_TEXT_GENERIC, useShareInvite } from '@/lib/hooks/use-share-invite'

describe('share default copy', () => {
  it('is the accepted variant-1 text with the honest 14-days-both motivator', () => {
    expect(SHARE_TEXT).toContain('Слушай, жутко точно: тут считают день по моей натальной карте — сфера за сферой всё про меня. Глянь свой, это 30 секунд:')
    expect(SHARE_TEXT).toContain('По моей ссылке мы оба получим по 14 дней полного доступа.')
  })

  it('never uses the word «гороскоп» without a negation nearby', () => {
    const idx = SHARE_TEXT.indexOf('гороскоп')
    if (idx !== -1) {
      const window = SHARE_TEXT.slice(Math.max(0, idx - 30), idx)
      expect(window.includes('Не ') || window.includes('не ')).toBe(true)
    }
  })

  it('is written on ты without esoteric pathos', () => {
    expect(SHARE_TEXT).toContain('Глянь')
    expect(SHARE_TEXT).toContain('свой')
    expect(SHARE_TEXT).not.toMatch(/судьба|звёзды велят|космос говорит|вселенная шепчет/i)
  })
})

describe('invite URL', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('keeps the working API inviteUrl form t.me/vi_astro_bot/app?startapp={id}', async () => {
    const apiUrl = 'https://t.me/vi_astro_bot/app?startapp=424242'
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      json: () => Promise.resolve({ inviteUrl: apiUrl }),
    }))

    const { result } = renderHook(() => useShareInvite())
    await waitFor(() => expect(vi.mocked(fetch)).toHaveBeenCalledTimes(1))

    const openTelegramLink = vi.fn()
    Object.defineProperty(window, 'Telegram', {
      value: { WebApp: { openTelegramLink } },
      configurable: true,
      writable: true,
    })

    // Wait for the inviteUrl state to settle from the API, then assert the
    // exact share URL built from it (never the ?start=ref_ form).
    await waitFor(() => {
      result.current()
      const last = openTelegramLink.mock.calls.at(-1)?.[0] ?? ''
      expect(last).toContain(encodeURIComponent(apiUrl))
    })

    const shareUrl = openTelegramLink.mock.calls.at(-1)![0] as string
    expect(shareUrl).toContain('https://t.me/share/url?url=')
    expect(shareUrl).toContain(encodeURIComponent(SHARE_TEXT))
    expect(shareUrl).not.toContain('start=ref_')
  })
})

describe('honest fallback without an attributed API link', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    delete (window as { Telegram?: unknown }).Telegram
  })

  it('falls back to the canonical startapp URL from the Telegram user id when the API fails', async () => {
    // The canonical startapp={id} link carries referral attribution (frontend
    // auto-claim reads start_param), so the 14-days-both motivator stays honest.
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const openTelegramLink = vi.fn()
    Object.defineProperty(window, 'Telegram', {
      value: { WebApp: { initDataUnsafe: { user: { id: 424242 } }, openTelegramLink } },
      configurable: true,
      writable: true,
    })

    const { result } = renderHook(() => useShareInvite())
    await act(async () => {}) // flush the rejected fetch

    result.current()
    const shareUrl = openTelegramLink.mock.calls.at(-1)![0] as string
    const decoded = decodeURIComponent(shareUrl)
    expect(decoded).toContain('https://t.me/vi_astro_bot/app?startapp=424242')
    expect(decoded).toContain('По моей ссылке мы оба получим по 14 дней полного доступа.')
    expect(decoded).not.toContain('start=invite')
  })

  it('shares the generic app link WITHOUT the bonus promise when no user id is available', async () => {
    // An unattributed link cannot grant a referral bonus, so the text must
    // degrade to the promise-free generic copy.
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')))
    const openTelegramLink = vi.fn()
    Object.defineProperty(window, 'Telegram', {
      value: { WebApp: { openTelegramLink } }, // no initDataUnsafe user id
      configurable: true,
      writable: true,
    })

    const { result } = renderHook(() => useShareInvite())
    await act(async () => {}) // flush the rejected fetch

    result.current()
    const shareUrl = openTelegramLink.mock.calls.at(-1)![0] as string
    const decoded = decodeURIComponent(shareUrl)
    expect(decoded).toContain('https://t.me/vi_astro_bot/app')
    expect(decoded).not.toContain('startapp')
    expect(decoded).not.toContain('мы оба получим')
    expect(decoded).toContain(SHARE_TEXT_GENERIC)
  })
})
