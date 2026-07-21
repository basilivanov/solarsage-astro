
// ############################################################################
// AI_HEADER: TEST_PROFILESCREEN_CANCEL_REFRESH — cancel status re-read contract.
// ROLE: Proves that after a SUCCESSFUL cancel the profile re-reads
//       SubscriptionStatusResponse (via hook statusRevision) and the UI
//       flips to honest non-renewing semantics, while a failed cancel never
//       touches the flags. Access stays "subscription" until period end.
// ############################################################################

import { beforeEach, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import React from "react"
import type { Profile } from "@/lib/profile"

const mockGetPaymentProducts = vi.fn()
const mockGetSubscriptionStatus = vi.fn()
const mockCancelSubscription = vi.fn()
const mockStartSubscription = vi.fn()

vi.mock("@/lib/api/payment", () => ({
  getPaymentProducts: (...args: unknown[]) => mockGetPaymentProducts(...args),
  getSubscriptionStatus: (...args: unknown[]) => mockGetSubscriptionStatus(...args),
  cancelSubscription: (...args: unknown[]) => mockCancelSubscription(...args),
  startSubscription: (...args: unknown[]) => mockStartSubscription(...args),
  paymentErrorMessage: (error: unknown) => (error instanceof Error ? error.message : "Ошибка"),
}))

vi.mock("@/hooks/use-profile", () => ({
  useProfile: () => ({
    profile: {
      firstName: "",
      birthDate: { day: "", month: "", year: "" },
      birthTime: { hours: "", minutes: "", unknown: true },
      birthPlace: "",
      currentCity: "",
      birthdayCity: "",
      birthLocation: null,
      currentLocation: null,
      birthdayLocation: null,
      gender: null,
      isOnboarded: true,
      sameAsBirth: false,
      birthdaySameAsCurrent: false,
    } satisfies Profile,
    update: vi.fn(),
    loaded: true,
    saving: false,
    error: null,
  }),
}))

vi.mock("@/hooks/use-telegram-user", () => ({
  useTelegramUser: () => null,
}))

vi.mock("@/lib/hooks/use-share-invite", () => ({
  useShareInvite: () => vi.fn(),
}))

vi.mock("@/components/profile/edit-sheet", () => ({
  EditSheet: () => <div role="dialog">edit sheet</div>,
}))
vi.mock("@/components/profile/referral-card", () => ({
  ReferralCard: () => <div />,
}))
vi.mock("@/components/profile/horary-card", () => ({
  HoraryCard: () => <div />,
}))
vi.mock("@/components/profile/checkin-statistics", () => ({
  CheckinStatistics: () => <section />,
}))

import { ProfileScreen } from "@/components/profile/profile-screen"

const subscriptionAccess = {
  state: "subscription" as const,
  hasAccess: true,
  accessStart: null,
  accessEnd: null,
  daysLeft: 30,
}

const profileMeta = {
  horary: {
    weeklyFreeAvailable: false,
    weeklyFreeExpiresAt: null,
    nextWeeklyFreeAt: null,
    bonusCredits: 0,
    paidCredits: 0,
    canPurchase: true,
  },
  referral: { count: 0, bonusDays: 0, rewardDays: 14, inviteUrl: "" },
}

const PRODUCTS = {
  products: [
    { slug: "subscription_month", name: "Месяц", description: null, productType: "subscription_recurrent", priceKopecks: 9900, currency: "RUB", periodDays: 30, horaryQuota: null },
    { slug: "subscription_year", name: "Год", description: null, productType: "subscription_recurrent", priceKopecks: 99900, currency: "RUB", periodDays: 365, horaryQuota: null },
  ],
}

const ACTIVE_STATUS = {
  subscriptionId: "s-1",
  productSlug: "subscription_month",
  status: "active",
  priceKopecks: 9900,
  currency: "RUB",
  currentPeriodEnd: "2026-08-20",
  nextChargeAt: "2026-08-20T00:00:00Z",
  hasAccess: true,
  accessUntil: "2026-08-19",
  renewing: true,
  cancelable: true,
}

const CANCELED_STATUS = {
  ...ACTIVE_STATUS,
  status: "canceled",
  nextChargeAt: null,
  renewing: false,
  cancelable: false,
}

function cardRoot(): HTMLElement {
  const el = document.querySelector("[data-renewal]")
  if (!el) throw new Error("access card root not found")
  return el as HTMLElement
}

describe("ProfileScreen cancel refresh contract", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetPaymentProducts.mockResolvedValue(PRODUCTS)
  })

  it("successful cancel re-reads status: cancel button hides, non-renewing shown, access stays subscription", async () => {
    mockGetSubscriptionStatus
      .mockResolvedValueOnce(ACTIVE_STATUS)
      .mockResolvedValueOnce(CANCELED_STATUS)
    mockCancelSubscription.mockResolvedValue(undefined)

    render(
      <ProfileScreen
        access={subscriptionAccess}
        currentState="subscription"
        profileMeta={profileMeta}
      />,
    )

    const cancelBtn = await screen.findByText("Отменить подписку")
    await waitFor(() => expect(cardRoot().getAttribute("data-cancelable")).toBe("true"))
    expect(cardRoot().getAttribute("data-renewal")).toBe("renewing")

    fireEvent.click(cancelBtn)

    // The successful cancel bumps statusRevision -> the status is re-read.
    await waitFor(() => expect(mockCancelSubscription).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(mockGetSubscriptionStatus).toHaveBeenCalledTimes(2))
    await waitFor(() => expect(screen.queryByText("Отменить подписку")).toBeNull())

    // Honest non-renewing semantics while access stays "subscription".
    expect(screen.getByText(/Без автопродления/)).toBeTruthy()
    expect(screen.getByText("Автопродление отключено")).toBeTruthy()
    expect(screen.getByTestId("profile-screen").getAttribute("data-access-state")).toBe("subscription")
    expect(cardRoot().getAttribute("data-renewal")).toBe("non-renewing")
    expect(cardRoot().getAttribute("data-cancelable")).toBe("false")
  })

  it("failed cancel keeps flags and never re-reads", async () => {
    mockGetSubscriptionStatus.mockResolvedValue(ACTIVE_STATUS)
    mockCancelSubscription.mockRejectedValue(new Error("boom"))

    render(
      <ProfileScreen
        access={subscriptionAccess}
        currentState="subscription"
        profileMeta={profileMeta}
      />,
    )

    const cancelBtn = await screen.findByText("Отменить подписку")
    fireEvent.click(cancelBtn)

    await screen.findByTestId("profile-billing-error")
    // No revision bump: exactly one status read, flags unchanged.
    expect(mockGetSubscriptionStatus).toHaveBeenCalledTimes(1)
    expect(screen.getByText("Отменить подписку")).toBeTruthy()
    expect(cardRoot().getAttribute("data-cancelable")).toBe("true")
  })
})
