// ############################################################################
// AI_HEADER: MODULE_HOOKS_USETELEGRAMAUTH_TEST
// ROLE: Unit tests for useTelegramAuth hook (Slice 01)
// DEPENDENCIES: vitest, @testing-library/react, hooks/use-telegram-auth, lib/telegram/start-param
// GRACE_ANCHORS: [USE_TELEGRAM_AUTH_TESTS]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-USE-TELEGRAM-AUTH
// purpose: Validate Telegram authentication lifecycle, dev vs production auth, start_param intent classification (referral vs promo vs ignored), promo localStorage persistence, URL cleanup, and PII log redaction.
// owns:
//   - __tests__/hooks/useTelegramAuth.test.ts
// inputs: mock window.Telegram, webApp context, fetch responses and start_params
// outputs: Vitest assertion results
// dependencies:
//   - M-HOOK-TELEGRAM-AUTH (useTelegramAuth)
//   - M-TELEGRAM-START-PARAM (PROMO_PENDING_SESSION_KEY)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-USE-TELEGRAM-AUTH

// START_MODULE_MAP: M-TESTS-USE-TELEGRAM-AUTH
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - AUTH_TESTS: test dev auth, production telegram auth, timeout, and duplicate prevention
//   - START_PARAM_TESTS: test referral auto-claim (numeric only), promo intent localStorage routing, ignored intent, URL cleanup, and PII log redaction
// owned_tests:
//   - __tests__/hooks/useTelegramAuth.test.ts
// END_MODULE_MAP: M-TESTS-USE-TELEGRAM-AUTH

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, waitFor } from "@testing-library/react"
import { PROMO_PENDING_SESSION_KEY } from "@/lib/telegram/start-param"

const { mockLogger, mockLogEvent } = vi.hoisted(() => ({
  mockLogger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
  mockLogEvent: vi.fn(),
}))

vi.mock("@/lib/log", () => ({
  logger: mockLogger,
  logEvent: mockLogEvent,
}))

const mockUseTelegram = vi.fn(() => ({
  webApp: null,
  loaded: true,
  inTelegram: false,
}))
vi.mock("@/components/telegram-provider", () => ({
  useTelegram: () => mockUseTelegram(),
}))

const originalTelegram = (window as any).Telegram
const originalEnv = { ...process.env }

beforeEach(() => {
  global.fetch = vi.fn()
  delete (window as any).Telegram
  delete (window as any).__astro_referral_claimed
  if (typeof window !== "undefined") {
    if (window.sessionStorage) window.sessionStorage.clear()
    if (window.localStorage) window.localStorage.clear()
  }
  mockLogger.debug.mockClear()
  mockLogger.info.mockClear()
  mockLogger.warn.mockClear()
  mockLogger.error.mockClear()
  mockLogEvent.mockClear()
  mockUseTelegram.mockReturnValue({ webApp: null, loaded: true, inTelegram: false })
})

afterEach(() => {
  process.env = originalEnv
  ;(window as any).Telegram = originalTelegram
  vi.restoreAllMocks()
})

import { useTelegramAuth } from "@/hooks/use-telegram-auth"

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
    json: async () => (ok ? {} : { detail: { code: "SELF_REFERRAL" } }),
  })
}

function setupTelegram(overrides: any = {}) {
  ;(window as any).Telegram = {
    WebApp: {
      initData: "auth_date=...&hash=...",
      initDataUnsafe: {},
      ...overrides,
    },
  }
}

const LONG_TIMEOUT = 15000

describe("useTelegramAuth", () => {
  it("authenticates via dev auth in development mode", async () => {
    ;(process.env as any).NODE_ENV = "development"
    mockDevAuthResponse(true, { userId: 1 })

    const { result } = renderHook(() => useTelegramAuth())

    expect(result.current.isLoading).toBe(true)

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
    expect(global.fetch).toHaveBeenCalledWith(
      "/api/auth/dev",
      expect.objectContaining({ method: "POST" })
    )
  })

  it("returns error when dev auth fails", async () => {
    ;(process.env as any).NODE_ENV = "development"
    mockDevAuthResponse(false)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: LONG_TIMEOUT }
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBeTruthy()
  })

  it("does not authenticate in non-dev, non-TG mode", async () => {
    ;(process.env as any).NODE_ENV = "production"

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: LONG_TIMEOUT }
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it("does not bypass backend auth when NEXT_PUBLIC_DEMO_MODE is true", async () => {
    ;(process.env as any).NODE_ENV = "production"
    ;(process.env as any).NEXT_PUBLIC_DEMO_MODE = "true"

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: LONG_TIMEOUT }
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(global.fetch).not.toHaveBeenCalled()
  })

  it("times out after 5 seconds", async () => {
    ;(process.env as any).NODE_ENV = "development"
    ;(global.fetch as any).mockImplementation(() => new Promise(() => {}))

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: 12000 }
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBe("Authentication timeout")
  }, 15000)

  it("authenticates via Telegram when WebApp is available", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram()
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/auth/telegram",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("initData"),
      })
    )
  })

  it("returns error when Telegram auth fails (preserves backend detail error)", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram()
    mockTelegramAuthResponse(false, "Invalid hash")

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: LONG_TIMEOUT }
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBe("Invalid hash")
  })

  it("auto-claims referral on auth with numeric start_param", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram({
      initDataUnsafe: { start_param: "123456", user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)
    mockReferralResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/referral/claim",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ referrer_code: "123456" }),
      })
    )
  })

  it("routes promo intent start_param to localStorage AFTER successful auth and skips referral claim", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram({
      initDataUnsafe: { start_param: "m7q4n9x2r5kd", user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    const referralCalls = (global.fetch as any).mock.calls.filter(
      ([url]: [string]) => url === "/api/referral/claim"
    )
    expect(referralCalls).toHaveLength(0)

    expect(window.localStorage.getItem(PROMO_PENDING_SESSION_KEY)).toBe("m7q4n9x2r5kd")
    expect(window.localStorage.getItem("__astro_referral_code")).toBeNull()
  })

  it("does not re-store a consumed promo token delivered again via start_param", async () => {
    ;(process.env as any).NODE_ENV = "production"
    const { markPromoTokenConsumed } = await import("@/lib/telegram/start-param")
    markPromoTokenConsumed("m7q4n9x2r5kd")
    setupTelegram({
      initDataUnsafe: { start_param: "m7q4n9x2r5kd", user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => expect(result.current.isAuthenticated).toBe(true),
      { timeout: LONG_TIMEOUT }
    )

    expect(window.localStorage.getItem(PROMO_PENDING_SESSION_KEY)).toBeNull()
  })

  it("falls back to parsing start_param from the raw initData string when initDataUnsafe misses it", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram({
      initData: "auth_date=123&start_param=m7q4n9x2r5kd&hash=abc123",
      initDataUnsafe: { user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => expect(result.current.isAuthenticated).toBe(true),
      { timeout: LONG_TIMEOUT }
    )

    expect(window.localStorage.getItem(PROMO_PENDING_SESSION_KEY)).toBe("m7q4n9x2r5kd")
  })

  it("stores promo intent on the dev-auth path before returning", async () => {
    ;(process.env as any).NODE_ENV = "development"
    const originalLocation = (window as any).location
    ;(window as any).location = new URL("https://example.com/?tgWebAppStartParam=m7q4n9x2r5kd")
    mockDevAuthResponse(true, { userId: 1 })

    try {
      const { result } = renderHook(() => useTelegramAuth())

      await waitFor(
        () => expect(result.current.isAuthenticated).toBe(true),
        { timeout: LONG_TIMEOUT }
      )

      expect(window.localStorage.getItem(PROMO_PENDING_SESSION_KEY)).toBe("m7q4n9x2r5kd")
    } finally {
      ;(window as any).location = originalLocation
    }
  })

  it("keeps the existing persisted numeric referral fallback when no new start_param is present", async () => {
    ;(process.env as any).NODE_ENV = "production"
    window.localStorage.setItem("__astro_referral_code", "246810")
    setupTelegram({
      initDataUnsafe: { user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)
    mockReferralResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => expect(result.current.isAuthenticated).toBe(true),
      { timeout: LONG_TIMEOUT }
    )

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/referral/claim",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ referrer_code: "246810" }),
      })
    )
  })

  it("never claims referral when promo start_param is present even if preloaded numeric code is in localStorage", async () => {
    ;(process.env as any).NODE_ENV = "production"
    window.localStorage.setItem("__astro_referral_code", "999888")
    setupTelegram({
      initDataUnsafe: { start_param: "m7q4n9x2r5kd", user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => expect(result.current.isAuthenticated).toBe(true),
      { timeout: LONG_TIMEOUT }
    )

    const referralCalls = (global.fetch as any).mock.calls.filter(
      ([url]: [string]) => url === "/api/referral/claim"
    )
    expect(referralCalls).toHaveLength(0)
    expect(window.localStorage.getItem(PROMO_PENDING_SESSION_KEY)).toBe("m7q4n9x2r5kd")
  })

  it("never claims referral when invalid raw start_param is present even if preloaded numeric code is in localStorage", async () => {
    ;(process.env as any).NODE_ENV = "production"
    window.localStorage.setItem("__astro_referral_code", "999888")
    setupTelegram({
      initDataUnsafe: { start_param: "invalid_raw_param_123", user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => expect(result.current.isAuthenticated).toBe(true),
      { timeout: LONG_TIMEOUT }
    )

    const referralCalls = (global.fetch as any).mock.calls.filter(
      ([url]: [string]) => url === "/api/referral/claim"
    )
    expect(referralCalls).toHaveLength(0)
  })

  it("auth remains successful when sessionStorage.setItem throws, logging safe frontend.flow_failed without leaking token or initData", async () => {
    ;(process.env as any).NODE_ENV = "production"
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("QuotaExceededError")
    })

    setupTelegram({
      initData: "auth_date=123&hash=secret_hash",
      initDataUnsafe: { start_param: "m7q4n9x2r5kd", user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => expect(result.current.isAuthenticated).toBe(true),
      { timeout: LONG_TIMEOUT }
    )

    expect(result.current.isAuthenticated).toBe(true)
    expect(result.current.error).toBeNull()

    expect(mockLogEvent).toHaveBeenCalledWith(
      "frontend.flow_failed",
      { operation: "promo.intent_store", reason_code: "session_storage_failed" },
      expect.objectContaining({
        level: "error",
        slice: "W-FRONTEND",
        module: "M-HOOK-TELEGRAM-AUTH",
        block: "START_PARAM_ROUTING",
      })
    )

    const allLogCalls = JSON.stringify(mockLogEvent.mock.calls)
    expect(allLogCalls).not.toContain("m7q4n9x2r5kd")
    expect(allLogCalls).not.toContain("secret_hash")
  })

  it("does NOT store promo token if Telegram auth fails", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram({
      initDataUnsafe: { start_param: "m7q4n9x2r5kd", user: { id: 1 } },
    })
    mockTelegramAuthResponse(false, "Invalid hash")

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isLoading).toBe(false)
      },
      { timeout: LONG_TIMEOUT }
    )

    expect(result.current.isAuthenticated).toBe(false)
    expect(window.localStorage.getItem(PROMO_PENDING_SESSION_KEY)).toBeNull()
  })

  it("reads start_param from URL query parameter when initDataUnsafe.start_param is missing, cleans URL, and stores promo token after auth", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram({
      initDataUnsafe: {}, // no start_param in initDataUnsafe
    })
    mockTelegramAuthResponse(true)

    const replaceStateSpy = vi.spyOn(window.history, "replaceState")

    delete (window as any).location
    ;(window as any).location = new URL("https://example.com/readings?tgWebAppStartParam=m7q4n9x2r5kd&other=abc#tab-2")

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    // Verify URL was cleaned with other query & hash preserved
    expect(replaceStateSpy).toHaveBeenCalledWith(
      window.history.state,
      "",
      "/readings?other=abc#tab-2"
    )

    // Verify promo token was successfully stored in localStorage
    expect(window.localStorage.getItem(PROMO_PENDING_SESSION_KEY)).toBe("m7q4n9x2r5kd")
  })

  it("ignores invalid start_param without creating storage keys or calling referral claim", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram({
      initDataUnsafe: { start_param: "invalid_start_param_123", user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    const referralCalls = (global.fetch as any).mock.calls.filter(
      ([url]: [string]) => url === "/api/referral/claim"
    )
    expect(referralCalls).toHaveLength(0)
    expect(window.localStorage.getItem(PROMO_PENDING_SESSION_KEY)).toBeNull()
    expect(window.localStorage.getItem("__astro_referral_code")).toBeNull()
  })

  it("cleans up old non-numeric referral code from localStorage on successful auth", async () => {
    ;(process.env as any).NODE_ENV = "production"
    window.localStorage.setItem("__astro_referral_code", "old_ref123_non_numeric")
    setupTelegram()
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    expect(window.localStorage.getItem("__astro_referral_code")).toBeNull()
  })

  it("skips self-referral when start_param matches own user id", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram({
      initDataUnsafe: { start_param: "123", user: { id: 123 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    const referralCalls = (global.fetch as any).mock.calls.filter(
      ([url]: [string]) => url === "/api/referral/claim"
    )
    expect(referralCalls).toHaveLength(0)
  })

  it("claims referral only once per session", async () => {
    ;(process.env as any).NODE_ENV = "production"
    ;(window as any).__astro_referral_claimed = true
    setupTelegram({
      initDataUnsafe: { start_param: "789012", user: { id: 2 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    const referralCalls = (global.fetch as any).mock.calls.filter(
      ([url]: [string]) => url === "/api/referral/claim"
    )
    expect(referralCalls).toHaveLength(0)
  })

  it("does not duplicate Telegram auth when provider catches up with same initData", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram()
    mockTelegramAuthResponse(true)

    mockUseTelegram.mockReturnValue({
      webApp: null,
      loaded: true,
      inTelegram: false,
    })

    const { result, rerender } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => expect(result.current.isAuthenticated).toBe(true),
      { timeout: LONG_TIMEOUT }
    )

    mockUseTelegram.mockReturnValue({
      webApp: (window as any).Telegram.WebApp,
      loaded: true,
      inTelegram: true,
    })
    rerender()

    await new Promise((r) => setTimeout(r, 500))

    const tgAuthCalls = (global.fetch as any).mock.calls.filter(
      ([url]: [string]) => url === "/api/auth/telegram"
    )
    expect(tgAuthCalls).toHaveLength(1)
  })

  it("allows Telegram auth when SDK appears after initial non-Telegram decision", async () => {
    ;(process.env as any).NODE_ENV = "production"

    delete (window as any).Telegram
    mockUseTelegram.mockReturnValue({
      webApp: null,
      loaded: true,
      inTelegram: false,
    })

    const { result, rerender } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => expect(result.current.isLoading).toBe(false),
      { timeout: LONG_TIMEOUT }
    )
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.error).toBeNull()

    setupTelegram()
    mockTelegramAuthResponse(true)

    mockUseTelegram.mockReturnValue({
      webApp: (window as any).Telegram.WebApp,
      loaded: true,
      inTelegram: true,
    })
    rerender()

    await waitFor(
      () => expect(result.current.isAuthenticated).toBe(true),
      { timeout: LONG_TIMEOUT }
    )

    expect(global.fetch).toHaveBeenCalledWith(
      "/api/auth/telegram",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining("initData"),
      })
    )
  })

  it("does not leak raw initData, start_param, promo tokens or referral codes in logger calls", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram({
      initData: "auth_date=123&hash=secret_hash_value",
      initDataUnsafe: { start_param: "m7q4n9x2r5kd", user: { id: 1 } },
    })
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    const allLogs = JSON.stringify([
      ...mockLogger.debug.mock.calls,
      ...mockLogger.info.mock.calls,
      ...mockLogger.warn.mock.calls,
      ...mockLogger.error.mock.calls,
    ])

    expect(allLogs).not.toContain("m7q4n9x2r5kd")
    expect(allLogs).not.toContain("secret_hash_value")
    expect(allLogs).not.toContain("auth_date=123")
  })
})
