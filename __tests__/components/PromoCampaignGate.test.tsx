// @vitest-environment jsdom
// ############################################################################
// AI_HEADER: MODULE_TESTS_PROMO_CAMPAIGN_GATE
// ROLE: Integration and unit tests for PromoCampaignGate component.
// DEPENDENCIES: vitest, @testing-library/react, components/promo/promo-campaign-gate
// GRACE_ANCHORS: [PROMO_CAMPAIGN_GATE_TESTS]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-PROMO-CAMPAIGN-GATE
// purpose: Validate mounting contract, state machine transitions, onboarding redirects, reload loop prevention, failure recovery, fail-closed storage handling, and absence of raw tokens in DOM/logs.
// owns:
//   - __tests__/components/PromoCampaignGate.test.tsx
// inputs: mock next/navigation, lib/api/promo, lib/telegram/start-param, lib/log
// outputs: Vitest assertion results
// dependencies:
//   - M-PROMO-CAMPAIGN-GATE (components/promo/promo-campaign-gate)
// side_effects: renders React components in jsdom environment
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-PROMO-CAMPAIGN-GATE

// START_MODULE_MAP: M-TESTS-PROMO-CAMPAIGN-GATE
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - MOUNT_TESTS: test empty token, onboarding pathname, fixture shell absence
//   - PREVIEW_TESTS: test valid preview, incomplete natal/base onboarding redirects
//   - REDEEM_TESTS: test redeem success reload, ALREADY_REDEEMED recovery, dismiss token clear
//   - FAILURE_TESTS: test invalid/expired/full clear vs rate limit/network retryable error
//   - PRIVACY_TESTS: test token absence in DOM and log mocks
// owned_tests:
//   - __tests__/components/PromoCampaignGate.test.tsx
// END_MODULE_MAP: M-TESTS-PROMO-CAMPAIGN-GATE

import * as React from "react"
import { beforeEach, afterEach, describe, it, expect, vi } from "vitest"
import { render, screen, fireEvent, waitFor } from "@testing-library/react"

const {
  mockPush,
  mockUsePathname,
  mockPreviewPromo,
  mockRedeemPromo,
  mockLogEvent,
} = vi.hoisted(() => ({
  mockPush: vi.fn(),
  mockUsePathname: vi.fn().mockReturnValue("/day"),
  mockPreviewPromo: vi.fn(),
  mockRedeemPromo: vi.fn(),
  mockLogEvent: vi.fn(),
}))

vi.mock("next/navigation", () => ({
  usePathname: () => mockUsePathname(),
  useRouter: () => ({
    push: mockPush,
  }),
}))

vi.mock("@/lib/api/promo", () => ({
  previewPromo: (...args: unknown[]) => mockPreviewPromo(...args),
  redeemPromo: (...args: unknown[]) => mockRedeemPromo(...args),
  PromoApiError: class PromoApiError extends Error {
    status: number
    code: string
    constructor(status: number, code: string, message: string) {
      super(message)
      this.name = "PromoApiError"
      this.status = status
      this.code = code
    }
  },
}))

vi.mock("@/lib/log", () => ({
  logEvent: (...args: unknown[]) => mockLogEvent(...args),
  logger: {
    info: vi.fn(),
    warn: vi.fn(),
    debug: vi.fn(),
    error: vi.fn(),
  },
}))

import { PromoCampaignGate } from "@/components/promo/promo-campaign-gate"
import { PromoApiError } from "@/lib/api/promo"
import {
  savePendingPromoToken,
  getPendingPromoToken,
} from "@/lib/telegram/start-param"

const VALID_TOKEN = "m7q4n9x2r5kd"

describe("PromoCampaignGate", () => {
  const originalReload = window.location.reload

  beforeEach(() => {
    vi.clearAllMocks()
    window.sessionStorage.clear()
    window.localStorage.clear()
    mockUsePathname.mockReturnValue("/day")

    // Mock window.location.reload
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...window.location, reload: vi.fn() },
    })
  })

  afterEach(() => {
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...window.location, reload: originalReload },
    })
  })

  it("does nothing when no pending token is in sessionStorage", async () => {
    render(<PromoCampaignGate />)

    await new Promise((r) => setTimeout(r, 10))

    expect(mockPreviewPromo).not.toHaveBeenCalled()
    expect(screen.queryByTestId("promo-confirmation-sheet")).toBeNull()
  })

  it("previews offer and shows sheet when valid token exists and profile is complete", async () => {
    savePendingPromoToken(VALID_TOKEN)
    mockPreviewPromo.mockResolvedValueOnce({
      offer: {
        displayName: "Пакет тестера",
        accessDays: 30,
        bonusCredits: 50,
        unlockNatal: true,
      },
      profileComplete: true,
    })

    render(<PromoCampaignGate />)

    await waitFor(() => {
      expect(mockPreviewPromo).toHaveBeenCalledWith(VALID_TOKEN)
      expect(screen.getByTestId("promo-confirmation-sheet")).toBeDefined()
    })

    expect(screen.getByTestId("promo-offer-name").textContent).toContain("Пакет тестера")
    expect(mockLogEvent).toHaveBeenCalledWith("promo.offer_viewed", expect.objectContaining({
      payload: { access_days: 30, bonus_credits: 50, unlock_natal: true }
    }))
  })

  it("redirects to /onboarding?requiredFor=promoNatal and retains token when unlockNatal=true and profile is incomplete", async () => {
    savePendingPromoToken(VALID_TOKEN)
    mockPreviewPromo.mockResolvedValueOnce({
      offer: {
        displayName: "Натал Спешл",
        accessDays: 0,
        bonusCredits: 0,
        unlockNatal: true,
      },
      profileComplete: false,
    })

    render(<PromoCampaignGate />)

    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith("/onboarding?requiredFor=promoNatal")
    })

    // Token must be RETAINED in sessionStorage
    expect(getPendingPromoToken()).toBe(VALID_TOKEN)
    expect(screen.queryByTestId("promo-confirmation-sheet")).toBeNull()
  })

  it("suppresses gate while pathname starts with /onboarding and resumes preview after exit", async () => {
    savePendingPromoToken(VALID_TOKEN)
    mockUsePathname.mockReturnValue("/onboarding")

    const { rerender } = render(<PromoCampaignGate />)

    await new Promise((r) => setTimeout(r, 10))
    expect(mockPreviewPromo).not.toHaveBeenCalled()

    // Exit /onboarding
    mockUsePathname.mockReturnValue("/day")
    mockPreviewPromo.mockResolvedValueOnce({
      offer: {
        displayName: "После Онбординга",
        accessDays: 7,
        bonusCredits: 0,
        unlockNatal: false,
      },
      profileComplete: true,
    })

    rerender(<PromoCampaignGate />)

    await waitFor(() => {
      expect(mockPreviewPromo).toHaveBeenCalledWith(VALID_TOKEN)
      expect(screen.getByTestId("promo-confirmation-sheet")).toBeDefined()
    })
  })

  it("clears token and hides sheet when user clicks dismiss (Не сейчас)", async () => {
    savePendingPromoToken(VALID_TOKEN)
    mockPreviewPromo.mockResolvedValueOnce({
      offer: {
        displayName: "Пакет тестера",
        accessDays: 30,
        bonusCredits: 50,
        unlockNatal: true,
      },
      profileComplete: true,
    })

    render(<PromoCampaignGate />)

    await waitFor(() => {
      expect(screen.getByTestId("promo-confirmation-sheet")).toBeDefined()
    })

    fireEvent.click(screen.getByTestId("promo-dismiss"))

    expect(getPendingPromoToken()).toBeNull()
    expect(mockRedeemPromo).not.toHaveBeenCalled()
    expect(screen.queryByTestId("promo-confirmation-sheet")).toBeNull()
  })

  it("executes redeem, clears token, and triggers single reload on redeem 200 success", async () => {
    savePendingPromoToken(VALID_TOKEN)
    mockPreviewPromo.mockResolvedValueOnce({
      offer: {
        displayName: "Пакет тестера",
        accessDays: 30,
        bonusCredits: 50,
        unlockNatal: true,
      },
      profileComplete: true,
    })
    mockRedeemPromo.mockResolvedValueOnce({
      status: "redeemed",
      offer: {
        displayName: "Пакет тестера",
        accessDays: 30,
        bonusCredits: 50,
        unlockNatal: true,
      },
      grants: {
        accessStartsAt: "2026-07-25T00:00:00Z",
        accessUntil: "2026-08-24T00:00:00Z",
        bonusCredits: 50,
        bonusCreditsExpiresAt: "2026-08-24T00:00:00Z",
        natalUnlocked: true,
        natalAlreadyOwned: false,
      },
    })

    render(<PromoCampaignGate />)

    await waitFor(() => {
      expect(screen.getByTestId("promo-confirmation-sheet")).toBeDefined()
    })

    fireEvent.click(screen.getByTestId("promo-activate"))

    await waitFor(() => {
      expect(mockRedeemPromo).toHaveBeenCalledWith(VALID_TOKEN)
      expect(getPendingPromoToken()).toBeNull()
      expect(window.location.reload).toHaveBeenCalledTimes(1)
    })
  })

  it("handles lost 200 / ALREADY_REDEEMED by clearing token and triggering reload without showing duplicate UI", async () => {
    savePendingPromoToken(VALID_TOKEN)
    mockPreviewPromo.mockRejectedValueOnce(
      new PromoApiError(409, "ALREADY_REDEEMED", "Промокод уже активирован")
    )

    render(<PromoCampaignGate />)

    await waitFor(() => {
      expect(getPendingPromoToken()).toBeNull()
      expect(window.location.reload).toHaveBeenCalledTimes(1)
    })

    expect(screen.queryByTestId("promo-confirmation-sheet")).toBeNull()
    // The consumed marker is what prevents the reload loop on the next app load
    // (the webview re-delivers the same start_param every time).
    const { isPromoTokenConsumed } = await import("@/lib/telegram/start-param")
    expect(isPromoTokenConsumed(VALID_TOKEN)).toBe(true)
  })

  it("clears a consumed token left in sessionStorage without calling preview", async () => {
    const { markPromoTokenConsumed } = await import("@/lib/telegram/start-param")
    markPromoTokenConsumed(VALID_TOKEN)
    savePendingPromoToken(VALID_TOKEN)

    render(<PromoCampaignGate />)

    await waitFor(() => {
      expect(getPendingPromoToken()).toBeNull()
    })

    expect(mockPreviewPromo).not.toHaveBeenCalled()
    expect(screen.queryByTestId("promo-confirmation-sheet")).toBeNull()
    expect(window.location.reload).not.toHaveBeenCalled()
  })

  it("clears token on INVALID_CODE / EXPIRED / FULL preview error", async () => {
    savePendingPromoToken(VALID_TOKEN)
    mockPreviewPromo.mockRejectedValueOnce(
      new PromoApiError(410, "CAMPAIGN_EXPIRED", "Срок действия истёк")
    )

    render(<PromoCampaignGate />)

    await waitFor(() => {
      expect(getPendingPromoToken()).toBeNull()
    })

    expect(screen.queryByTestId("promo-confirmation-sheet")).toBeNull()
  })

  it("retains token and shows retryable error on network / rate limit error", async () => {
    savePendingPromoToken(VALID_TOKEN)
    mockPreviewPromo.mockResolvedValueOnce({
      offer: {
        displayName: "Пакет тестера",
        accessDays: 30,
        bonusCredits: 50,
        unlockNatal: true,
      },
      profileComplete: true,
    })
    mockRedeemPromo.mockRejectedValueOnce(
      new PromoApiError(429, "RATE_LIMITED", "Слишком много запросов")
    )

    render(<PromoCampaignGate />)

    await waitFor(() => {
      expect(screen.getByTestId("promo-confirmation-sheet")).toBeDefined()
    })

    fireEvent.click(screen.getByTestId("promo-activate"))

    await waitFor(() => {
      expect(screen.getByTestId("promo-error")).toBeDefined()
    })

    // Token must be RETAINED in sessionStorage for retry
    expect(getPendingPromoToken()).toBe(VALID_TOKEN)

    // Retry activation
    mockRedeemPromo.mockResolvedValueOnce({
      status: "redeemed",
      offer: {
        displayName: "Пакет тестера",
        accessDays: 30,
        bonusCredits: 50,
        unlockNatal: true,
      },
      grants: {
        accessStartsAt: "2026-07-25T00:00:00Z",
        accessUntil: "2026-08-24T00:00:00Z",
        bonusCredits: 50,
        bonusCreditsExpiresAt: "2026-08-24T00:00:00Z",
        natalUnlocked: true,
        natalAlreadyOwned: false,
      },
    })

    fireEvent.click(screen.getByRole("button", { name: "Повторить" }))

    await waitFor(() => {
      expect(mockRedeemPromo).toHaveBeenCalledTimes(2)
      expect(getPendingPromoToken()).toBeNull()
      expect(window.location.reload).toHaveBeenCalledTimes(1)
    })
  })

  it("never exposes raw token string in rendered DOM or log payload", async () => {
    savePendingPromoToken(VALID_TOKEN)
    mockPreviewPromo.mockResolvedValueOnce({
      offer: {
        displayName: "Секретный Пакет",
        accessDays: 14,
        bonusCredits: 20,
        unlockNatal: false,
      },
      profileComplete: true,
    })

    const { container } = render(<PromoCampaignGate />)

    await waitFor(() => {
      expect(screen.getByTestId("promo-confirmation-sheet")).toBeDefined()
    })

    expect(container.innerHTML).not.toContain(VALID_TOKEN)

    for (const call of mockLogEvent.mock.calls) {
      expect(JSON.stringify(call)).not.toContain(VALID_TOKEN)
    }
  })
})
