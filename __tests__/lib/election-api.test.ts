import { describe, it, expect } from "vitest"
import { ElectionSearchSchema } from "@/lib/contracts/election"

describe("Election Zod Contracts", () => {
  it("parses valid top-level camelCase search payload with snake_case result payload", () => {
    const rawPayload = {
      id: "34cdf627-7ca2-4864-b3dd-42b96e0515f7",
      eventType: "wedding",
      windowFrom: "2026-08-01",
      windowTo: "2026-08-05",
      status: "done",
      createdAt: "2026-07-23T20:00:00Z",
      result: {
        event: "wedding",
        best_days: [
          {
            date: "2026-08-01",
            score: 85,
            label: "great",
            reasons: ["Луна в Тельце"],
          },
        ],
        avoid_days: [],
      },
    }

    const parsed = ElectionSearchSchema.parse(rawPayload)
    expect(parsed.eventType).toBe("wedding")
    expect(parsed.result?.best_days).toHaveLength(1)
    expect(parsed.result?.best_days[0].score).toBe(85)
  })
})
