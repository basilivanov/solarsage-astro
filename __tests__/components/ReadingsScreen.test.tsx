import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import React from "react"

const mockPush = vi.fn()
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: mockPush }),
}))

vi.mock("@/components/readings/available-card", () => ({
  AvailableCard: ({ title, onClick, route }: { title: string; onClick: () => void; route?: string }) => (
    <button data-testid={`readings-card-${route?.replace("/readings/", "") ?? ""}`} data-href={route} onClick={onClick}>
      {title}
    </button>
  ),
}))
vi.mock("@/components/readings/coming-card", () => ({
  ComingCard: ({ title, onClick }: { title: string; onClick: () => void }) => (
    <button data-testid={`readings-card-${title.toLowerCase().replace(/\s+/g, "-")}`} onClick={onClick}>
      {title}
    </button>
  ),
}))
vi.mock("@/components/readings/in-dev-overlay", () => ({
  InDevOverlay: ({ onClose }: { onClose: () => void }) => (
    <div role="dialog" data-testid="readings-in-dev-overlay">
      <button onClick={onClose}>close</button>
    </div>
  ),
}))

import { ReadingsScreen } from "@/components/readings/readings-screen"

describe("ReadingsScreen", () => {
  it("root element has data-testid and data-state", () => {
    render(<ReadingsScreen />)
    expect(screen.getByTestId("readings-screen").getAttribute("data-state")).toBe("ready")
  })

  it("renders header, info banner, and available section", () => {
    render(<ReadingsScreen />)
    expect(screen.getByTestId("readings-header")).toBeTruthy()
    expect(screen.getByTestId("readings-info-banner")).toBeTruthy()
    expect(screen.getByTestId("readings-available-section")).toBeTruthy()
    expect(screen.getByTestId("readings-available-list")).toBeTruthy()
  })

  it("renders horary and natal cards with route targets", () => {
    render(<ReadingsScreen />)
    const horary = screen.getByTestId("readings-card-horary")
    const natal = screen.getByTestId("readings-card-natal")
    expect(horary).toBeTruthy()
    expect(natal).toBeTruthy()
    expect(horary.getAttribute("data-href")).toBe("/readings/horary")
    expect(natal.getAttribute("data-href")).toBe("/readings/natal")
  })

  it("clicking horary card navigates to /readings/horary", () => {
    render(<ReadingsScreen />)
    fireEvent.click(screen.getByTestId("readings-card-horary"))
    expect(mockPush).toHaveBeenCalledWith("/readings/horary")
  })

  it("clicking natal card navigates to /readings/natal", () => {
    render(<ReadingsScreen />)
    fireEvent.click(screen.getByTestId("readings-card-natal"))
    expect(mockPush).toHaveBeenCalledWith("/readings/natal")
  })

  it("renders coming section with coming cards", () => {
    render(<ReadingsScreen />)
    expect(screen.getByTestId("readings-coming-section")).toBeTruthy()
    expect(screen.getByTestId("readings-coming-list")).toBeTruthy()
  })

  it("clicking coming card opens in-dev-overlay", () => {
    render(<ReadingsScreen />)
    const firstComing = screen.getByTestId("readings-card-прогноз-на-месяц")
    expect(firstComing).toBeTruthy()
    fireEvent.click(firstComing)
    expect(screen.getByTestId("readings-in-dev-overlay")).toBeTruthy()
  })

  it("in-dev-overlay is dismissible", () => {
    render(<ReadingsScreen />)
    fireEvent.click(screen.getByTestId("readings-card-прогноз-на-месяц"))
    expect(screen.getByTestId("readings-in-dev-overlay")).toBeTruthy()
    fireEvent.click(screen.getByText("close"))
    expect(screen.queryByTestId("readings-in-dev-overlay")).toBeNull()
  })
})
