import { fireEvent, render, screen } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { SynastryAddSheet } from "@/components/synastry/synastry-add-sheet"

vi.mock("@/lib/api/synastry", () => ({
  createSynastryPartner: vi.fn().mockResolvedValue({
    reportId: "rep-123",
    partnerId: "partner-123",
    state: "pending",
  }),
}))

describe("SynastryAddSheet", () => {
  it("renders modal sheet with data-testid=synastry-add-sheet and role=dialog", () => {
    const onClose = vi.fn()
    const onSuccess = vi.fn()

    render(<SynastryAddSheet open={true} onClose={onClose} onSuccess={onSuccess} />)

    const sheet = screen.getByTestId("synastry-add-sheet")
    expect(sheet).toBeDefined()
    expect(sheet.getAttribute("role")).toBe("dialog")
    expect(sheet.getAttribute("aria-modal")).toBe("true")

    const switchBtn = screen.getByRole("switch")
    expect(switchBtn).toBeDefined()
    expect(switchBtn.getAttribute("aria-checked")).toBe("false")
  })

  it("toggles unknown time switch and disables birth time input", () => {
    const onClose = vi.fn()
    const onSuccess = vi.fn()

    render(<SynastryAddSheet open={true} onClose={onClose} onSuccess={onSuccess} />)

    const switchBtn = screen.getByRole("switch")
    const timeInput = screen.getByLabelText("Время рождения") as HTMLInputElement

    expect(timeInput.disabled).toBe(false)
    fireEvent.click(switchBtn)

    expect(switchBtn.getAttribute("aria-checked")).toBe("true")
    expect(timeInput.disabled).toBe(true)
    expect(screen.getByText(/Примерный расчёт/i)).toBeDefined()
  })
})
