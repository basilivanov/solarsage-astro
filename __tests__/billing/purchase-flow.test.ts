// ############################################################################
// AI_HEADER: TEST_PURCHASE_FLOW — redirect + bounded polling contract.
// ROLE: Proves lib/billing/purchase-flow.ts: Telegram-safe open chain,
//       terminal-state polling with backoff, timeout failure, and that only
//       authenticated local endpoints decide success.
// ############################################################################

import { beforeEach, describe, expect, it, vi } from "vitest"

const mockGetPurchaseStatus = vi.fn()
const mockGetSubscriptionStatus = vi.fn()

vi.mock("@/lib/api/payment", () => ({
  getPurchaseStatus: (...args: unknown[]) => mockGetPurchaseStatus(...args),
  getSubscriptionStatus: (...args: unknown[]) => mockGetSubscriptionStatus(...args),
}))

import {
  PurchasePollTimeoutError,
  openProviderCheckout,
  pollPurchaseStatus,
  pollSubscriptionStatus,
} from "@/lib/billing/purchase-flow"

const instantSleep = () => Promise.resolve()

describe("lib/billing/purchase-flow", () => {
  beforeEach(() => {
    mockGetPurchaseStatus.mockReset()
    mockGetSubscriptionStatus.mockReset()
    vi.unstubAllGlobals()
  })

  it("openProviderCheckout prefers Telegram openLink over window.open", () => {
    const openLink = vi.fn()
    const winOpen = vi.fn()
    vi.stubGlobal("Telegram", { WebApp: { openLink } })
    vi.stubGlobal("open", winOpen)
    openProviderCheckout("https://pay.example/c")
    expect(openLink).toHaveBeenCalledWith("https://pay.example/c")
    expect(winOpen).not.toHaveBeenCalled()
  })

  it("openProviderCheckout falls back to window.open without Telegram", () => {
    const winOpen = vi.fn()
    vi.stubGlobal("Telegram", undefined)
    vi.stubGlobal("open", winOpen)
    openProviderCheckout("https://pay.example/c")
    expect(winOpen).toHaveBeenCalledWith("https://pay.example/c", "_blank", "noopener,noreferrer")
  })

  it("pollPurchaseStatus resolves on terminal status after pending reads", async () => {
    mockGetPurchaseStatus
      .mockResolvedValueOnce({ status: "pending" })
      .mockResolvedValueOnce({ status: "pending" })
      .mockResolvedValueOnce({ status: "consumed" })
    const result = await pollPurchaseStatus("p1", { sleep: instantSleep, intervalMs: 1, maxIntervalMs: 2 })
    expect(result.status).toBe("consumed")
    expect(mockGetPurchaseStatus).toHaveBeenCalledTimes(3)
    expect(mockGetPurchaseStatus).toHaveBeenCalledWith("p1")
  })

  it("pollPurchaseStatus throws PurchasePollTimeoutError on timeout", async () => {
    mockGetPurchaseStatus.mockResolvedValue({ status: "pending" })
    await expect(
      pollPurchaseStatus("p1", { sleep: instantSleep, intervalMs: 1, maxIntervalMs: 1, timeoutMs: -1 })
    ).rejects.toBeInstanceOf(PurchasePollTimeoutError)
  })

  it("pollSubscriptionStatus stops only on confirmed access, never on pending", async () => {
    mockGetSubscriptionStatus
      .mockResolvedValueOnce({ status: "pending", hasAccess: false })
      .mockResolvedValueOnce({ status: "active", hasAccess: true })
    const result = await pollSubscriptionStatus({ sleep: instantSleep, intervalMs: 1, maxIntervalMs: 2 })
    expect(result.status).toBe("active")
    expect(mockGetSubscriptionStatus).toHaveBeenCalledTimes(2)
  })
})
