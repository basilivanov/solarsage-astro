import { beforeEach, describe, expect, it, vi } from "vitest"

import {
  createCheckin,
  formatDateInTimeZone,
  getCheckin,
  getCheckinMetrics,
  getYesterdayCheckin,
} from "@/lib/api/checkin"

describe("check-in API client", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it("posts the real numeric check-in payload with credentials", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 7,
        targetDate: "2026-07-06",
        mood: 5,
        accuracy: 3,
        energy: 4,
        tags: ["calm"],
        note: "Real note",
        streak: 2,
        filledAt: "2026-07-06T20:00:00Z",
        createdAt: "2026-07-06T20:00:00Z",
      }),
    })

    await createCheckin({
      targetDate: "2026-07-06",
      mood: 5,
      accuracy: 3,
      energy: 4,
      tags: ["calm"],
      note: "Real note",
    })

    expect(global.fetch).toHaveBeenCalledWith("/api/checkin", {
      method: "POST",
      credentials: "include",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        targetDate: "2026-07-06",
        mood: 5,
        accuracy: 3,
        energy: 4,
        tags: ["calm"],
        note: "Real note",
      }),
    })
  })

  it("formats a date in the supplied profile timezone instead of UTC ISO date", () => {
    const instant = new Date("2026-01-01T10:30:00.000Z")

    expect(instant.toISOString().split("T")[0]).toBe("2026-01-01")
    expect(formatDateInTimeZone(instant, "Pacific/Kiritimati")).toBe("2026-01-02")
    expect(formatDateInTimeZone(instant, "America/Los_Angeles")).toBe("2026-01-01")
  })

  it("returns null from GET when backend sends the null wrapper", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ checkin: null }),
    })

    await expect(getCheckin("2026-07-06")).resolves.toBeNull()
    expect(global.fetch).toHaveBeenCalledWith("/api/checkin/2026-07-06", {
      credentials: "include",
      headers: { Accept: "application/json" },
    })
  })

  it("throws backend detail messages without falling back to demo data", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "invalid check-in" }),
    })

    await expect(
      createCheckin({
        targetDate: "2026-07-06",
        mood: 5,
        accuracy: 3,
        energy: 4,
        tags: [],
        note: null,
      }),
    ).rejects.toThrow("invalid check-in")
  })

  it("calls yesterday and metrics real endpoints", async () => {
    global.fetch = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ hadCheckin: false, checkin: null }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          totalCheckins: 0,
          currentStreak: 0,
          longestStreak: 0,
          averageMood: 0,
          averageEnergy: null,
          averageAccuracy: null,
          moodDistribution: {},
          accuracyDistribution: {},
          tagFrequency: {},
        }),
      })

    await getYesterdayCheckin()
    await getCheckinMetrics({ from: "2026-07-01", to: "2026-07-31" })

    expect(global.fetch).toHaveBeenNthCalledWith(1, "/api/checkin/yesterday", {
      credentials: "include",
      headers: { Accept: "application/json" },
    })
    expect(global.fetch).toHaveBeenNthCalledWith(
      2,
      "/api/checkin/metrics?from=2026-07-01&to=2026-07-31",
      {
        credentials: "include",
        headers: { Accept: "application/json" },
      },
    )
  })
})
