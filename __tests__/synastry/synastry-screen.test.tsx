import { fireEvent, render, screen } from "@testing-library/react"
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
      counters: { good: 8, mid: 2, bad: 2 },
      reportState: "ready",
      createdAt: "2026-07-25T12:00:00Z",
    },
  ]),
  deleteSynastryPartner: vi.fn().mockResolvedValue(undefined),
}))

describe("SynastryScreen", () => {
  it("renders hero, search filters, and list items with data-testid=synastry-screen", async () => {
    const onSelect = vi.fn()
    render(<SynastryScreen onSelectPartner={onSelect} />)

    const root = screen.getByTestId("synastry-screen")
    expect(root).toBeDefined()

    expect(screen.getByTestId("synastry-list-hero")).toBeDefined()
    expect(screen.getByTestId("synastry-search-filters")).toBeDefined()

    const partnerCard = await screen.findByTestId("synastry-card")
    expect(partnerCard).toBeDefined()
    expect(partnerCard.getAttribute("data-status")).toBe("good")
    expect(screen.getByText("Максим")).toBeDefined()
    expect(screen.getByText("89")).toBeDefined()
  })

  it("filters partners list by search query", async () => {
    render(<SynastryScreen onSelectPartner={vi.fn()} />)

    await screen.findByTestId("synastry-card")

    const searchInput = screen.getByTestId("synastry-search-input")
    fireEvent.change(searchInput, { target: { value: "Ольга" } })

    expect(screen.queryByText("Максим")).toBeNull()
    expect(screen.getByText("По этому имени никого нет")).toBeDefined()
  })
})
