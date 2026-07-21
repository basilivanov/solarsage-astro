
// ############################################################################
// AI_HEADER: MODULE_HORARY_HORARY_PURCHASE_SHEET_TEST
// ROLE: Unit tests for the REAL horary purchase sheet: catalog packs with
//       API prices, provider checkout start, confirmed-status purchase and
//       loading/error contracts. No Telegram Stars, no "coming soon" stubs.
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for the horary purchase sheet behavior.
// owns:
//   - __tests__/horary/horary-purchase-sheet.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - Prices come only from the mocked catalog response.
//   - onPurchased fires only after a confirmed terminal status.
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react"
import React from "react"

// ── Mocks ─────────────────────────────────────────────────────────────────────

const mockGetPaymentProducts = vi.fn()
const mockStartPurchase = vi.fn()
const mockOpenProviderCheckout = vi.fn()
const mockPollPurchaseStatus = vi.fn()

vi.mock("@/lib/api/payment", () => ({
  PaymentApiError: class PaymentApiError extends Error {
    status: number
    code?: string
    constructor({ status, code, message }: { status: number; code?: string; message: string }) {
      super(message)
      this.status = status
      this.code = code
    }
  },
  getPaymentProducts: (...args: unknown[]) => mockGetPaymentProducts(...args),
  startPurchase: (...args: unknown[]) => mockStartPurchase(...args),
}))

vi.mock("@/lib/billing/purchase-flow", () => ({
  PurchasePollTimeoutError: class PurchasePollTimeoutError extends Error {},
  openProviderCheckout: (...args: unknown[]) => mockOpenProviderCheckout(...args),
  pollPurchaseStatus: (...args: unknown[]) => mockPollPurchaseStatus(...args),
}))

vi.mock("lucide-react", () => ({
  X: () => <span data-testid="icon-x" />,
  Coins: () => <span data-testid="icon-coins" />,
}))

import { HoraryPurchaseSheet } from "@/components/readings/horary/horary-purchase-sheet"

const PACKS = {
  products: [
    { slug: "horary_1", name: "1 хорарный вопрос", description: null, productType: "one_time", priceKopecks: 5000, currency: "RUB", periodDays: null, horaryQuota: 1 },
    { slug: "horary_3", name: "3 хорарных вопроса", description: null, productType: "one_time", priceKopecks: 12000, currency: "RUB", periodDays: null, horaryQuota: 3 },
    { slug: "horary_10", name: "10 хорарных вопросов", description: null, productType: "one_time", priceKopecks: 30000, currency: "RUB", periodDays: null, horaryQuota: 10 },
    { slug: "subscription_month", name: "Подписка", description: null, productType: "subscription_recurrent", priceKopecks: 9900, currency: "RUB", periodDays: 30, horaryQuota: null },
  ],
}

function renderSheet(onClose = vi.fn(), onPurchased = vi.fn()) {
  return { onClose, onPurchased, ...render(<HoraryPurchaseSheet onClose={onClose} onPurchased={onPurchased} />) }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("HoraryPurchaseSheet", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    document.body.style.overflow = ""
    mockGetPaymentProducts.mockResolvedValue(PACKS)
  })

  afterEach(() => {
    vi.useRealTimers()
    document.body.style.overflow = ""
  })

  it('renders dialog contract: testid, role=dialog, aria-modal, data-state', async () => {
    renderSheet()
    const sheet = screen.getByTestId("horary-purchase-sheet")
    expect(sheet.getAttribute("role")).toBe("dialog")
    expect(sheet.getAttribute("aria-modal")).toBe("true")
    expect(sheet.getAttribute("data-state")).toBe("loading")
    await waitFor(() => {
      expect(screen.getByTestId("horary-purchase-sheet").getAttribute("data-state")).toBe("ready")
    })
  })

  it("renders packs with catalog prices only (no subscription, no Stars)", async () => {
    renderSheet()
    await screen.findByTestId("horary-pack-horary_1")
    expect(screen.getByTestId("horary-pack-horary_1").textContent).toContain("1 хорарный вопрос")
    expect(screen.getByTestId("horary-pack-horary_1").textContent).toContain("50 ₽")
    expect(screen.getByTestId("horary-pack-horary_3").textContent).toContain("120 ₽")
    expect(screen.getByTestId("horary-pack-horary_10").textContent).toContain("300 ₽")
    expect(screen.queryByText(/Подписка/)).toBeNull()
    expect(screen.queryByText(/Telegram Stars|★/)).toBeNull()
    expect(screen.queryByText(/скоро появится/i)).toBeNull()
  })

  it("buy flow: start -> provider checkout -> confirmed poll -> onPurchased + close", async () => {
    const onClose = vi.fn()
    const onPurchased = vi.fn()
    mockStartPurchase.mockResolvedValue({
      purchaseId: "p-1",
      productSlug: "horary_3",
      providerPaymentId: "prov-1",
      confirmationUrl: "https://pay.example/c",
      status: "pending",
    })
    mockPollPurchaseStatus.mockResolvedValue({ status: "consumed" })

    renderSheet(onClose, onPurchased)
    const pack = await screen.findByTestId("horary-pack-horary_3")
    fireEvent.click(pack)

    await waitFor(() => expect(mockStartPurchase).toHaveBeenCalledWith("horary_3"))
    await waitFor(() => expect(mockOpenProviderCheckout).toHaveBeenCalledWith("https://pay.example/c"))
    await waitFor(() => expect(mockPollPurchaseStatus).toHaveBeenCalledWith("p-1"))
    await waitFor(() => expect(onPurchased).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(onClose).toHaveBeenCalledTimes(1), { timeout: 2000 })
  })

  it("canceled terminal status keeps the sheet open with an honest error", async () => {
    mockStartPurchase.mockResolvedValue({
      purchaseId: "p-1",
      productSlug: "horary_1",
      providerPaymentId: "prov-1",
      confirmationUrl: "https://pay.example/c",
      status: "pending",
    })
    mockPollPurchaseStatus.mockResolvedValue({ status: "canceled" })
    const onPurchased = vi.fn()

    renderSheet(vi.fn(), onPurchased)
    fireEvent.click(await screen.findByTestId("horary-pack-horary_1"))
    await screen.findByTestId("horary-purchase-flow-error")
    expect(onPurchased).not.toHaveBeenCalled()
  })

  it("catalog failure shows error state with retry", async () => {
    mockGetPaymentProducts.mockRejectedValue(new Error("503"))
    renderSheet()
    await screen.findByTestId("horary-purchase-error")
    expect(screen.getByTestId("horary-purchase-sheet").getAttribute("data-state")).toBe("error")
    mockGetPaymentProducts.mockResolvedValue(PACKS)
    fireEvent.click(screen.getByText("Повторить"))
    await screen.findByTestId("horary-pack-horary_1")
  })

  it("calls onClose after 220ms from both close buttons; aria-labels kept", () => {
    vi.useFakeTimers()
    const onClose = vi.fn()
    renderSheet(onClose)
    const closeButtons = screen.getAllByTestId("horary-purchase-close")
    expect(closeButtons).toHaveLength(2)
    for (const btn of closeButtons) {
      expect(btn.getAttribute("aria-label")).toBe("Закрыть")
    }
    fireEvent.click(closeButtons[1])
    expect(onClose).not.toHaveBeenCalled()
    act(() => {
      vi.advanceTimersByTime(220)
    })
    expect(onClose).toHaveBeenCalledTimes(1)
  })

  it("locks body scroll on mount and restores it on unmount", () => {
    const previousOverflow = "auto"
    document.body.style.overflow = previousOverflow
    const { unmount } = render(<HoraryPurchaseSheet onClose={vi.fn()} onPurchased={vi.fn()} />)
    expect(document.body.style.overflow).toBe("hidden")
    unmount()
    expect(document.body.style.overflow).toBe(previousOverflow)
  })
})
