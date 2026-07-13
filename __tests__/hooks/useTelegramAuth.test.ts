
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USETELEGRAMAUTH_TEST
// ROLE: Unit tests for useTelegramAuth.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for useTelegramAuthts behavior
// owns:
//   - __tests__/hooks/useTelegramAuth.test.ts
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

// Provide a default mock for useTelegram so tests work without a
// <TelegramProvider> wrapper. Tests that set window.Telegram directly
// (setupTelegram) still work via the fallback path in useTelegramAuth.
const mockUseTelegram = vi.fn(() => ({
  webApp: null,
  loaded: true,  // In tests there is no dynamic SDK loading; act as if loaded
  inTelegram: false,
}))
vi.mock('@/components/telegram-provider', () => ({
  useTelegram: () => mockUseTelegram(),
}))

const originalTelegram = (window as any).Telegram
const originalEnv = { ...process.env }

beforeEach(() => {
  global.fetch = vi.fn()
  delete (window as any).Telegram
  delete (window as any).__astro_referral_claimed
  // Reset mock to default (loaded: true so effect runs; webApp: null so hooks
  // decide auth strategy by checking window.Telegram fallback)
  mockUseTelegram.mockReturnValue({ webApp: null, loaded: true, inTelegram: false })
})

afterEach(() => {
  process.env = originalEnv
  ;(window as any).Telegram = originalTelegram
})

import { useTelegramAuth } from '@/hooks/use-telegram-auth'

function mockDevAuthResponse(ok: boolean, data: Record<string, unknown> = {}) {
  ;(global.fetch as any).mockResolvedValueOnce({
    ok,
    status: ok ? 200 : 401,
    json: async () => data,
  })
}

function mockTelegramAuthResponse(ok: boolean, detail?: string) {
  ;(global.fetch as any).mockResolvedValueOnce({
    ok,
    status: ok ? 200 : 401,
    json: async () => (detail ? { detail } : { userId: 123 }),
  })
}

function mockReferralResponse(ok: boolean = true) {
  ;(global.fetch as any).mockResolvedValueOnce({
    ok,
    status: ok ? 200 : 400,
    json: async () => (ok ? {} : { detail: { code: 'SELF_REFERRAL' } }),
  })
}

function setupTelegram(overrides: any = {}) {
  ;(window as any).Telegram = {
    WebApp: {
      initData: 'auth_date=...&hash=...',
      initDataUnsafe: {},
      ...overrides,
    },
  }
}

const LONG_TIMEOUT = 15000

describe('useTelegramAuth', () => {

  it('authenticates via dev auth in development mode', async () => {
    (process.env as any).NODE_ENV = 'development'
    mockDevAuthResponse(true, { userId: 1 })

    const { result } = renderHook(() => useTelegramAuth())

    expect(result.current.isLoading).toBe(true)

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT },
    )

    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(global.fetch).toHaveBeenCalledWith(
      '/api/auth/dev',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('returns error when dev auth fails', async () => {
    (process.env as any).NODE_ENV = 'development'
    mockDevAuthResponse(false)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: LONG_TIMEOUT },
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBeTruthy()
  })

  it('does not authenticate in non-dev, non-TG mode', async () => {
    (process.env as any).NODE_ENV = 'production'

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: LONG_TIMEOUT },
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('does not bypass backend auth when NEXT_PUBLIC_DEMO_MODE is true', async () => {
    (process.env as any).NODE_ENV = 'production'
    ;(process.env as any).NEXT_PUBLIC_DEMO_MODE = 'true'

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: LONG_TIMEOUT },
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it('times out after 5 seconds', async () => {
    (process.env as any).NODE_ENV = 'development'
    ;(global.fetch as any).mockImplementation(() => new Promise(() => {}))

    const { result } = renderHook(() => useTelegramAuth())

    // Wait for the loading to go false (triggered by 5s timeout)
    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: 12000 },
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBe('Authentication timeout')
  }, 15000) // vitest test timeout

  it('authenticates via Telegram when WebApp is available', async () => {
    (process.env as any).NODE_ENV = 'production'
    setupTelegram()
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT },
    )

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/auth/telegram',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('initData'),
      }),
    )
  })

  it('returns error when Telegram auth fails', async () => {
    (process.env as any).NODE_ENV = 'production'
    setupTelegram()
    mockTelegramAuthResponse(false, 'Invalid hash')

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: LONG_TIMEOUT },
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBe('Invalid hash')
  })

  it('auto-claims referral on auth with start_param', async () => {
    (process.env as any).NODE_ENV = 'production'
    setupTelegram({
      initDataUnsafe: { start_param: 'ref123', user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)
    mockReferralResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT },
    )

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/referral/claim',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('skips self-referral when start_param matches own user id', async () => {
    (process.env as any).NODE_ENV = 'production'
    setupTelegram({
      initDataUnsafe: { start_param: '123', user: { id: 123 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT },
    )

    const referralCalls = (global.fetch as any).mock.calls.filter(
      ([url]: [string]) => url === '/api/referral/claim',
    )
    expect(referralCalls).toHaveLength(0)
  })

  it('claims referral only once per session', async () => {
    (process.env as any).NODE_ENV = 'production'
    // Set claim key to simulate already claimed
    ;(window as any).__astro_referral_claimed = true
    setupTelegram({
      initDataUnsafe: { start_param: 'ref789', user: { id: 2 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT },
    )

    const referralCalls = (global.fetch as any).mock.calls.filter(
      ([url]: [string]) => url === '/api/referral/claim',
    )
    expect(referralCalls).toHaveLength(0)
  })

  it('does not duplicate Telegram auth when provider catches up with same initData', async () => {
    (process.env as any).NODE_ENV = 'production'
    setupTelegram()

    // Only one auth response mock — a second call would throw / hang
    mockTelegramAuthResponse(true)

    // First render: loaded=true but webApp=null → effect uses fallbackTg
    mockUseTelegram.mockReturnValue({
      webApp: null,
      loaded: true,
      inTelegram: false,
    })

    const { result, rerender } = renderHook(() => useTelegramAuth())

    // Auth completes via the fallback
    await waitFor(
      () => expect(result.current.isAuthenticated).toBe(true),
      { timeout: LONG_TIMEOUT },
    )

    // Now provider catches up — mock returns the same webApp (same initData key)
    mockUseTelegram.mockReturnValue({
      webApp: (window as any).Telegram.WebApp,
      loaded: true,
      inTelegram: true,
    })
    rerender()

    // Small delay: if the guard fails, a second authenticate() would call
    // global.fetch again and throw because no mock is set up.  The hook's
    // catch would set error — no crash but we'd see a second auth call.
    await new Promise((r) => setTimeout(r, 500))

    // Only one call to /api/auth/telegram
    const tgAuthCalls = (global.fetch as any).mock.calls.filter(
      ([url]: [string]) => url === '/api/auth/telegram',
    )
    expect(tgAuthCalls).toHaveLength(1)
  })

  it('allows Telegram auth when SDK appears after initial non-Telegram decision', async () => {
    (process.env as any).NODE_ENV = 'production'

    // No Telegram at first — simulate non-Telegram environment
    delete (window as any).Telegram
    mockUseTelegram.mockReturnValue({
      webApp: null,
      loaded: true,
      inTelegram: false,
    })

    const { result, rerender } = renderHook(() => useTelegramAuth())

    // First decision: no Telegram → skip auth gracefully
    await waitFor(
      () => expect(result.current.isLoading).toBe(false),
      { timeout: LONG_TIMEOUT },
    )
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBeNull()

    // Now Telegram SDK "loads" — window.Telegram appears with real initData
    setupTelegram()
    mockTelegramAuthResponse(true)

    mockUseTelegram.mockReturnValue({
      webApp: (window as any).Telegram.WebApp,
      loaded: true,
      inTelegram: true,
    })
    rerender()

    // Second decision: Telegram auth should fire now (key changed from 'none' to initData)
    await waitFor(
      () => expect(result.current.isAuthenticated).toBe(true),
      { timeout: LONG_TIMEOUT },
    )

    expect(global.fetch).toHaveBeenCalledWith(
      '/api/auth/telegram',
      expect.objectContaining({
        method: 'POST',
        body: expect.stringContaining('initData'),
      }),
    )
  })
})
