import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { SynastryDetailScreen } from "@/components/synastry/synastry-detail-screen"

vi.mock("@/lib/api/synastry", () => ({
  getSynastryReport: vi.fn().mockResolvedValue({
    id: "rep-123",
    ownerId: "user-1",
    partnerId: "partner-123",
    partnerName: "Ирина",
    relationType: "romantic",
    precision: "exact",
    score: 78,
    status: "good",
    verdict: "Хорошая гармония",
    summary: "Партнёры отлично дополняют друг друга.",
    counters: { good: 5, mid: 2, bad: 1 },
    aspects: [
      {
        id: "sun_trine_moon",
        title: "Солнце трин Луна",
        tone: "good",
        score: 90,
        description: "Естественная гармония эмоционального и сознательного.",
        techSignature: "Sun trine Moon",
      },
    ],
    houseOverlays: [],
    spheres: [
      { id: "intimacy", title: "Близость", score: 85, description: "Высокая эмоциональная близость." },
    ],
    translations: [
      {
        tone: "good",
        title: "Взаимная поддержка",
        aspectId: "sun_trine_moon",
        tech: "Солнце трин Луна",
        text: "Естественное понимание потребностей друг друга.",
        scene: "Совместное принятие решений проходит легко.",
      },
    ],
    userFeedback: null,
    createdAt: "2026-07-25T12:00:00Z",
  }),
  submitSynastryFeedback: vi.fn().mockResolvedValue({ reportId: "rep-123", value: "accurate", updatedAt: "2026-07-25T12:05:00Z" }),
  getAspectDrilldown: vi.fn().mockResolvedValue({
    aspectId: "sun_trine_moon",
    title: "Солнце трин Луна",
    tone: "good",
    techSignature: "Sun trine Moon",
    explanation: "Глубокая психологическая связь.",
    scenario: "Принятие решений проходит легко.",
    advice: "Развивайте открытость.",
  }),
}))

describe("SynastryDetailScreen", () => {
  it("renders detail screen with hero, score panel, aspect list, translations, spheres, and feedback", async () => {
    const onBack = vi.fn()
    render(<SynastryDetailScreen partnerId="partner-123" onBack={onBack} />)

    const screenRoot = await screen.findByTestId("synastry-detail-screen")
    expect(screenRoot).toBeDefined()

    expect(screen.getByTestId("synastry-hero")).toBeDefined()
    expect(screen.getByTestId("synastry-score")).toBeDefined()
    expect(screen.getByTestId("synastry-wheel")).toBeDefined()
    expect(screen.getByTestId("synastry-translations")).toBeDefined()
    expect(screen.getByTestId("synastry-spheres")).toBeDefined()
    expect(screen.getByTestId("synastry-feedback")).toBeDefined()

    expect(screen.getByText("Ты + Ирина")).toBeDefined()
    expect(screen.getByText("78")).toBeDefined()
    expect(screen.getByText("Взаимная поддержка")).toBeDefined()
  })
})
