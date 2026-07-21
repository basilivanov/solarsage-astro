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
  SubscriptionTerminalError,
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

  it("pollSubscriptionStatus succeeds only on the EXACT started id reaching active", async () => {
    // Referral hasAccess=true and a foreign active subscription must be
    // ignored — the wait continues until OUR id is active.
    mockGetSubscriptionStatus
      .mockResolvedValueOnce({ subscriptionId: "foreign", status: "active", hasAccess: true })
      .mockResolvedValueOnce({ subscriptionId: "s-1", status: "pending", hasAccess: true })
      .mockResolvedValueOnce({ subscriptionId: "s-1", status: "active", hasAccess: true })
    const result = await pollSubscriptionStatus("s-1", { sleep: instantSleep, intervalMs: 1, maxIntervalMs: 2 })
    expect(result.status).toBe("active")
    expect(mockGetSubscriptionStatus).toHaveBeenCalledTimes(3)
  })

  it("pollSubscriptionStatus keeps waiting on referral access without our id", async () => {
    mockGetSubscriptionStatus.mockResolvedValue({ subscriptionId: null, status: "none", hasAccess: true })
    await expect(
      pollSubscriptionStatus("s-1", { sleep: instantSleep, intervalMs: 1, maxIntervalMs: 1, timeoutMs: -1 })
    ).rejects.toBeInstanceOf(PurchasePollTimeoutError)
  })

  it("pollSubscriptionStatus fails fast on exact canceled (no 5-minute wait)", async () => {
    mockGetSubscriptionStatus
      .mockResolvedValueOnce({ subscriptionId: "s-1", status: "pending", hasAccess: false })
      .mockResolvedValueOnce({ subscriptionId: "s-1", status: "canceled", hasAccess: false })
    await expect(
      pollSubscriptionStatus("s-1", { sleep: instantSleep, intervalMs: 1, maxIntervalMs: 2 })
    ).rejects.toBeInstanceOf(SubscriptionTerminalError)
    expect(mockGetSubscriptionStatus).toHaveBeenCalledTimes(2)
  })

  it("pollSubscriptionStatus fails fast on exact expired", async () => {
    mockGetSubscriptionStatus.mockResolvedValue({ subscriptionId: "s-1", status: "expired", hasAccess: false })
    await expect(
      pollSubscriptionStatus("s-1", { sleep: instantSleep, intervalMs: 1, maxIntervalMs: 2 })
    ).rejects.toBeInstanceOf(SubscriptionTerminalError)
  })
})
