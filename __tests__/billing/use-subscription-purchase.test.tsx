
// ############################################################################
// AI_HEADER: TEST_USE_SUBSCRIPTION_PURCHASE — subscription flow hook contract.
// ROLE: Proves lib/hooks/use-subscription-purchase.ts: catalog-driven
//       products, start->checkout->confirmed-poll success path, unavailable
//       and error states. Success only from the authenticated status poll.
// ############################################################################

import { beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"

const mockGetPaymentProducts = vi.fn()
const mockStartSubscription = vi.fn()
const mockCancelSubscription = vi.fn()
const mockOpenProviderCheckout = vi.fn()
const mockPollSubscriptionStatus = vi.fn()

vi.mock("@/lib/api/payment", () => ({
  PaymentApiError: class PaymentApiError extends Error {
    status: number
    code?: string
    constructor({ status, code, message }: { status: number; code?: string; message: string }) {
      super(message)
      this.name = "PaymentApiError"
      this.status = status
      this.code = code
    }
  },
  paymentErrorMessage: (error: unknown) =>
    error instanceof Error ? error.message : "Не удалось выполнить платёжный запрос.",
  getPaymentProducts: (...args: unknown[]) => mockGetPaymentProducts(...args),
  startSubscription: (...args: unknown[]) => mockStartSubscription(...args),
  cancelSubscription: (...args: unknown[]) => mockCancelSubscription(...args),
}))

vi.mock("@/lib/billing/purchase-flow", () => ({
  PurchasePollTimeoutError: class PurchasePollTimeoutError extends Error {},
  SubscriptionTerminalError: class SubscriptionTerminalError extends Error {
    constructor(message: string) {
      super(message)
      this.name = "SubscriptionTerminalError"
    }
  },
  openProviderCheckout: (...args: unknown[]) => mockOpenProviderCheckout(...args),
  pollSubscriptionStatus: (...args: unknown[]) => mockPollSubscriptionStatus(...args),
}))

import { SubscriptionTerminalError } from "@/lib/billing/purchase-flow"
import { useSubscriptionPurchase } from "@/lib/hooks/use-subscription-purchase"

const PRODUCTS = {
  products: [
    { slug: "subscription_month", name: "Месяц", description: null, productType: "subscription_recurrent", priceKopecks: 9900, currency: "RUB", periodDays: 30, horaryQuota: null },
    { slug: "subscription_year", name: "Год", description: null, productType: "subscription_recurrent", priceKopecks: 99900, currency: "RUB", periodDays: 365, horaryQuota: null },
  ],
}

describe("useSubscriptionPurchase", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetPaymentProducts.mockResolvedValue(PRODUCTS)
  })

  it("loads the catalog and exposes month/year products", async () => {
    const { result } = renderHook(() => useSubscriptionPurchase())
    await waitFor(() => expect(result.current.ready).toBe(true))
    expect(result.current.month?.priceKopecks).toBe(9900)
    expect(result.current.year?.priceKopecks).toBe(99900)
    expect(result.current.unavailable).toBe(false)
  })

  it("marks billing unavailable when the catalog fails", async () => {
    mockGetPaymentProducts.mockRejectedValue(new Error("503"))
    const { result } = renderHook(() => useSubscriptionPurchase())
    await waitFor(() => expect(result.current.unavailable).toBe(true))
    expect(result.current.ready).toBe(false)
  })

  it("buy: start -> provider checkout -> confirmed poll -> success + onActivated", async () => {
    const onActivated = vi.fn()
    mockStartSubscription.mockResolvedValue({
      subscriptionId: "s-1",
      productSlug: "subscription_month",
      providerPaymentId: "prov-1",
      confirmationUrl: "https://pay.example/c",
      status: "pending",
    })
    mockPollSubscriptionStatus.mockResolvedValue({ status: "active", hasAccess: true })

    const { result } = renderHook(() => useSubscriptionPurchase(onActivated))
    await waitFor(() => expect(result.current.ready).toBe(true))
    await act(async () => {
      await result.current.buy("subscription_month")
    })

    expect(mockStartSubscription).toHaveBeenCalledWith("subscription_month")
    expect(mockOpenProviderCheckout).toHaveBeenCalledWith("https://pay.example/c")
    expect(mockPollSubscriptionStatus).toHaveBeenCalledWith("s-1")
    expect(result.current.phase).toBe("success")
    expect(onActivated).toHaveBeenCalledTimes(1)
  })

  it("buy: exact canceled poll ends in an honest terminal error", async () => {
    const onActivated = vi.fn()
    mockStartSubscription.mockResolvedValue({
      subscriptionId: "s-1",
      productSlug: "subscription_month",
      providerPaymentId: "prov-1",
      confirmationUrl: "https://pay.example/c",
      status: "pending",
    })
    mockPollSubscriptionStatus.mockRejectedValue(new SubscriptionTerminalError("Подписка не активировалась"))
    const { result } = renderHook(() => useSubscriptionPurchase(onActivated))
    await waitFor(() => expect(result.current.ready).toBe(true))
    await act(async () => {
      await result.current.buy("subscription_month")
    })
    expect(result.current.phase).toBe("error")
    expect(result.current.errorMessage).toContain("не активировалась")
    expect(onActivated).not.toHaveBeenCalled()
  })

  it("buy failure lands in phase=error with a message, never success", async () => {
    const onActivated = vi.fn()
    mockStartSubscription.mockRejectedValue(new Error("boom"))
    const { result } = renderHook(() => useSubscriptionPurchase(onActivated))
    await waitFor(() => expect(result.current.ready).toBe(true))
    await act(async () => {
      await result.current.buy("subscription_year")
    })
    expect(result.current.phase).toBe("error")
    expect(result.current.errorMessage).toBeTruthy()
    expect(onActivated).not.toHaveBeenCalled()
  })

  it("cancel calls the API and refreshes the caller", async () => {
    const onActivated = vi.fn()
    mockCancelSubscription.mockResolvedValue(undefined)
    const { result } = renderHook(() => useSubscriptionPurchase(onActivated))
    await waitFor(() => expect(result.current.ready).toBe(true))
    await act(async () => {
      await result.current.cancel()
    })
    expect(mockCancelSubscription).toHaveBeenCalledTimes(1)
    expect(onActivated).toHaveBeenCalledTimes(1)
  })
})
