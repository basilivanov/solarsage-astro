// ############################################################################
// AI_HEADER: MODULE_HOOKS_USETELEGRAMAUTH_TEST
// ROLE: Unit tests for the shared useTelegramAuth store, auth deadline race and retry
// DEPENDENCIES: vitest, @testing-library/react, hooks/use-telegram-auth, lib/telegram/start-param
// GRACE_ANCHORS: [USE_TELEGRAM_AUTH_TESTS]
// WAVE: W-AUTH-TIMEOUT-RACE-FIX
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-USE-TELEGRAM-AUTH
// purpose: Validate the shared singleton auth state (one POST, one deadline), the 12 s timeout race, retry(), dev vs production auth, start_param intent classification (referral vs promo vs ignored), promo localStorage persistence, URL cleanup, and PII log redaction.
// owns:
//   - __tests__/hooks/useTelegramAuth.test.ts
// inputs: mock window.Telegram, webApp context, fetch responses, hash initData, fake timers and start_params
// outputs: Vitest assertion results
// dependencies:
//   - M-HOOK-TELEGRAM-AUTH (useTelegramAuth, AUTH_TIMEOUT_MS, __resetTelegramAuthForTests)
//   - M-TELEGRAM-START-PARAM (PROMO_PENDING_SESSION_KEY)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-USE-TELEGRAM-AUTH

// START_MODULE_MAP: M-TESTS-USE-TELEGRAM-AUTH
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - AUTH_TESTS: dev/production auth, shared store, duplicate prevention
//   - DEADLINE_TESTS: 12 s budget, race window, retry after timeout
//   - START_PARAM_TESTS: referral auto-claim (numeric only), promo intent localStorage routing, ignored intent, URL cleanup, PII log redaction
// owned_tests:
//   - __tests__/hooks/useTelegramAuth.test.ts
// END_MODULE_MAP: M-TESTS-USE-TELEGRAM-AUTH

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { renderHook, waitFor, act, cleanup } from "@testing-library/react"
import { PROMO_PENDING_SESSION_KEY } from "@/lib/telegram/start-param"
import {
  useTelegramAuth,
  AUTH_TIMEOUT_MS,
  __resetTelegramAuthForTests,
} from "@/hooks/use-telegram-auth"

const { mockLogger, mockLogEvent, mockSendBeaconEvent } = vi.hoisted(() => ({
  mockLogger: {
    debug: vi.fn(),
    info: vi.fn(),
    warn: vi.fn(),
    error: vi.fn(),
  },
  mockLogEvent: vi.fn(),
  mockSendBeaconEvent: vi.fn(),
}))

vi.mock("@/lib/log", () => ({
  logger: mockLogger,
  logEvent: mockLogEvent,
}))

vi.mock("@/lib/log/beacon", () => ({
  sendBeaconEvent: mockSendBeaconEvent,
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
const originalLocation = window.location
const originalEnv = { ...process.env }

beforeEach(() => {
  __resetTelegramAuthForTests()
  vi.useRealTimers()
  global.fetch = vi.fn()
  delete (window as any).Telegram
  delete (window as any).__astro_referral_claimed
  if (typeof window !== "undefined") {
    if (window.sessionStorage) window.sessionStorage.clear()
    if (window.localStorage) window.localStorage.clear()
  }
  window.history.replaceState({}, "", "/")
  mockLogger.debug.mockClear()
  mockLogger.info.mockClear()
  mockLogger.warn.mockClear()
  mockLogger.error.mockClear()
  mockLogEvent.mockClear()
  mockSendBeaconEvent.mockClear()
  mockUseTelegram.mockReturnValue({ webApp: null, loaded: true, inTelegram: false })
})

afterEach(() => {
  cleanup()
  __resetTelegramAuthForTests()
  vi.useRealTimers()
  process.env = originalEnv
  ;(window as any).Telegram = originalTelegram
  delete (window as any).location
  ;(window as any).location = originalLocation
  window.history.replaceState({}, "", "/")
  vi.restoreAllMocks()
})

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

function deferredResponse() {
  let resolve!: (value: unknown) => void
  const promise = new Promise((r) => {
    resolve = r
  })
  return { promise, resolve }
}

/** Flush pending microtasks inside act (fetch continuations). */
async function flushMicrotasks() {
  await act(async () => {
    await Promise.resolve()
  })
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

  it("sends auth.ok with platform and version after successful Telegram auth", async () => {
    ;(process.env as any).NODE_ENV = "production"
    setupTelegram()
    window.history.replaceState(
      {},
      "",
      "/#tgWebAppPlatform=ios&tgWebAppVersion=9.5"
    )
    mockTelegramAuthResponse(true)

    const { result } = renderHook(() => useTelegramAuth())

    await waitFor(
      () => {
        expect(result.current.isAuthenticated).toBe(true)
      },
      { timeout: LONG_TIMEOUT }
    )

    expect(mockSendBeaconEvent).toHaveBeenCalledWith(
      "auth.ok",
      expect.objectContaining({ platform: "ios", version: "9.5" }),
      expect.any(Object)
    )
  })
})

describe("useTelegramAuth error and routing behavior", () => {
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

  describe("auth deadline race and shared store", () => {
    it("a. succeeds with an 11s response inside the 12s budget and the deadline is cancelled", async () => {
      vi.useFakeTimers()
      ;(process.env as any).NODE_ENV = "production"
      setupTelegram()
      const pending = deferredResponse()
      ;(global.fetch as any).mockReturnValueOnce(pending.promise)

      const { result } = renderHook(() => useTelegramAuth())

      expect(result.current.isLoading).toBe(true)

      await act(async () => {
        await vi.advanceTimersByTimeAsync(11_000)
      })

      pending.resolve({ ok: true, status: 200, json: async () => ({ userId: 1 }) })
      await flushMicrotasks()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(600)
      })

      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.error).toBeNull()

      // Deadline was cleared on the response: crossing the 12 s mark changes nothing.
      await act(async () => {
        await vi.advanceTimersByTimeAsync(3_000)
      })
      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.error).toBeNull()
    })

    it("b. commits Authentication timeout for a response after the 12s budget", async () => {
      vi.useFakeTimers()
      ;(process.env as any).NODE_ENV = "production"
      setupTelegram()
      const pending = deferredResponse()
      ;(global.fetch as any).mockReturnValueOnce(pending.promise)

      const { result } = renderHook(() => useTelegramAuth())

      await act(async () => {
        await vi.advanceTimersByTimeAsync(AUTH_TIMEOUT_MS)
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBe("Authentication timeout")

      const warnPayload = JSON.stringify(mockLogger.warn.mock.calls)
      expect(warnPayload).toContain("timeout_budget_ms")
      expect(warnPayload).toContain("elapsed_ms")

      // A late 200 response must not overwrite the timeout error.
      pending.resolve({ ok: true, status: 200, json: async () => ({ userId: 1 }) })
      await flushMicrotasks()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(1_000)
      })

      expect(result.current.isAuthenticated).toBe(false)
      expect(result.current.error).toBe("Authentication timeout")
    })

    it("c. ends in a terminal error after 12s when the SDK never loads and there is no initData", async () => {
      vi.useFakeTimers()
      ;(process.env as any).NODE_ENV = "production"
      delete (window as any).Telegram
      mockUseTelegram.mockReturnValue({ webApp: null, loaded: false, inTelegram: false })

      const { result } = renderHook(() => useTelegramAuth())

      expect(result.current.isLoading).toBe(true)
      expect(global.fetch).not.toHaveBeenCalled()

      await act(async () => {
        await vi.advanceTimersByTimeAsync(AUTH_TIMEOUT_MS)
      })

      expect(result.current.isLoading).toBe(false)
      expect(result.current.error).toBe("Authentication timeout")
    })

    it("d. shares one POST between two simultaneously mounted hook instances", async () => {
      ;(process.env as any).NODE_ENV = "production"
      setupTelegram()
      mockTelegramAuthResponse(true)

      const first = renderHook(() => useTelegramAuth())
      const second = renderHook(() => useTelegramAuth())

      await waitFor(
        () => expect(first.result.current.isAuthenticated).toBe(true),
        { timeout: LONG_TIMEOUT }
      )
      await waitFor(
        () => expect(second.result.current.isAuthenticated).toBe(true),
        { timeout: LONG_TIMEOUT }
      )

      const tgAuthCalls = (global.fetch as any).mock.calls.filter(
        ([url]: [string]) => url === "/api/auth/telegram"
      )
      expect(tgAuthCalls).toHaveLength(1)
    })

    it("e. retry() after a timeout starts a fresh attempt with a new deadline and can authenticate", async () => {
      vi.useFakeTimers()
      ;(process.env as any).NODE_ENV = "production"
      setupTelegram()
      ;(global.fetch as any).mockImplementationOnce(() => new Promise(() => {}))
      ;(global.fetch as any).mockResolvedValueOnce({
        ok: true,
        status: 200,
        json: async () => ({ userId: 1 }),
      })

      const { result } = renderHook(() => useTelegramAuth())

      await act(async () => {
        await vi.advanceTimersByTimeAsync(AUTH_TIMEOUT_MS)
      })
      expect(result.current.error).toBe("Authentication timeout")

      act(() => {
        result.current.retry()
      })
      expect(result.current.isLoading).toBe(true)
      expect(result.current.error).toBeNull()

      await flushMicrotasks()
      await act(async () => {
        await vi.advanceTimersByTimeAsync(600)
      })

      expect(result.current.isAuthenticated).toBe(true)
      expect(result.current.error).toBeNull()

      const tgAuthCalls = (global.fetch as any).mock.calls.filter(
        ([url]: [string]) => url === "/api/auth/telegram"
      )
      expect(tgAuthCalls).toHaveLength(2)
    })

    it("f. authenticates immediately from the #tgWebAppData hash without any SDK", async () => {
      ;(process.env as any).NODE_ENV = "production"
      delete (window as any).Telegram
      const initData = "auth_date=123&hash=hash_from_url"
      window.history.replaceState({}, "", `/#tgWebAppData=${encodeURIComponent(initData)}`)
      mockUseTelegram.mockReturnValue({ webApp: null, loaded: true, inTelegram: false })
      mockTelegramAuthResponse(true)

      const { result } = renderHook(() => useTelegramAuth())

      await waitFor(
        () => expect(result.current.isAuthenticated).toBe(true),
        { timeout: LONG_TIMEOUT }
      )

      expect(global.fetch).toHaveBeenCalledWith(
        "/api/auth/telegram",
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("hash_from_url"),
        })
      )
    })
  })
})
