import { render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { SynastryScreen } from "@/components/synastry/synastry-screen"

vi.mock("@/lib/api/synastry", () => ({
  getSynastryPartners: vi.fn().mockResolvedValue([
    {
      id: "partner-123",
      name: "Максим",
      relationType: "romantic",
      birthDate: "1987-09-09",
      precision: "exact",
      score: 89,
      status: "good",
      summary: "Отличная совместимость пара.",
      createdAt: "2026-07-25T12:00:00Z",
    },
  ]),
  deleteSynastryPartner: vi.fn().mockResolvedValue(undefined),
}))

describe("SynastryScreen", () => {
  it("renders with data-testid=synastry-screen and list items", async () => {
    const onSelect = vi.fn()
    render(<SynastryScreen onSelectPartner={onSelect} />)

    const root = screen.getByTestId("synastry-screen")
    expect(root).toBeDefined()

    const partnerCard = await screen.findByTestId("synastry-card")
    expect(partnerCard).toBeDefined()
    expect(partnerCard.getAttribute("data-status")).toBe("good")
    expect(screen.getByText("Максим")).toBeDefined()
    expect(screen.getByText("89")).toBeDefined()
  })
})
