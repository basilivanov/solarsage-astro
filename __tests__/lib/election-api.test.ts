import { describe, it, expect } from "vitest"
import { ElectionSearchSchema } from "@/lib/contracts/election"

describe("Election Zod Contracts v2", () => {
  it("parses valid top-level camelCase search payload with v2 result payload containing facts and narrative", () => {
    const rawPayload = {
      id: "34cdf627-7ca2-4864-b3dd-42b96e0515f7",
      eventType: "relations:wedding",
      windowFrom: "2026-08-01",
      windowTo: "2026-08-05",
      status: "done",
      createdAt: "2026-07-24T08:00:00Z",
      result: {
        event: "relations:wedding",
        best_days: [
          {
            date: "2026-08-01",
            score: 85,
            label: "great",
            reasons: ["Луна в Тельце"],
            moon_sign_ru: "Телец",
            phase_pct: 75,
            voc_intervals: ["10:00-14:00"],
          },
        ],
        avoid_days: [],
        days: [
          {
            date: "2026-08-01",
            score: 85,
            label: "great",
            reasons: ["Луна в Тельце"],
          },
        ],
        facts: {
          event: { category: "relations", sub: "wedding", label: "Свадьба" },
          personal: { natal_moon_sign_ru: "Телец", resonates: true },
        },
        narrative: {
          hero_reason: "Идеальный день.",
          hero_personal: "Совпадает с наталом.",
          hero_plain: "Стабильный знак.",
          hero_hours: "До 14:00.",
          day_notes: [{ date: "2026-08-01", note: "Хороший выбор." }],
          avoid_notes: [],
        },
      },
    }

    const parsed = ElectionSearchSchema.parse(rawPayload)
    expect(parsed.eventType).toBe("relations:wedding")
    expect(parsed.result?.facts?.event?.category).toBe("relations")
    expect(parsed.result?.narrative?.hero_reason).toBe("Идеальный день.")
  })
})
