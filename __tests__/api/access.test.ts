// ############################################################################
// AI_HEADER: MODULE_API_ACCESS_TEST
// ROLE: Unit tests for access.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
import { beforeEach, describe, expect, it, vi } from "vitest"
import { getAccess } from "../../lib/api/access"

describe("getAccess", () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it("fetches the authenticated backend access summary", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        user: "trial",
        referralDaysLeft: 8,
        subscriptionActive: false,
        accessStart: "2026-07-01",
        accessUntil: "2026-07-08",
      }),
    })

    const info = await getAccess()

    expect(fetch).toHaveBeenCalledWith("/api/access", {
      credentials: "include",
      headers: { Accept: "application/json" },
    })
    expect(info).toEqual({
      state: "trial",
      hasAccess: true,
      accessStart: new Date("2026-07-01T00:00:00"),
      accessEnd: new Date("2026-07-08T00:00:00"),
      daysLeft: 8,
    })
  })

  it("maps subscription and expired summaries without synthetic durations", async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          user: "subscription",
          referralDaysLeft: 0,
          subscriptionActive: true,
          accessStart: "2026-07-01",
          accessUntil: "2026-07-30",
        }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          user: "expired",
          referralDaysLeft: 0,
          subscriptionActive: false,
          accessStart: "2026-05-01",
          accessUntil: "2026-05-30",
        }),
      })

    const subscription = await getAccess()
    const expired = await getAccess()

    expect(subscription.state).toBe("subscription")
    expect(subscription.daysLeft).toBe(0)
    expect(subscription.accessEnd).toEqual(new Date("2026-07-30T00:00:00"))
    expect(expired).toMatchObject({
      state: "expired",
      hasAccess: false,
      daysLeft: 0,
    })
  })

  it("throws the backend detail on HTTP errors", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      json: async () => ({ detail: { message: "Session expired" } }),
    })

    await expect(getAccess()).rejects.toThrow("Session expired")
  })
})
