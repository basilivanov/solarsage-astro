import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { SynastryAddSheet } from "@/components/synastry/synastry-add-sheet"
import { createSynastryPartner } from "@/lib/api/synastry"

vi.mock("@/lib/api/synastry", () => ({
  createSynastryPartner: vi.fn().mockResolvedValue({
    reportId: "rep-123",
    partnerId: "partner-123",
    state: "pending",
  }),
}))

vi.mock("@/lib/api/cities", () => ({
  getPopularCities: vi.fn().mockReturnValue([
    { id: 1, name: "Москва", country: "Россия", lat: 55.7558, lon: 37.6173, timezone: "Europe/Moscow" },
  ]),
  searchCitiesAsync: vi.fn().mockResolvedValue([]),
}))

vi.mock("@/lib/api/geo", () => ({
  getTimezone: vi.fn().mockResolvedValue({ timezone_id: "Europe/Moscow" }),
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

  it("submits partner with city coordinates and timezone from CityPicker", async () => {
    window.HTMLElement.prototype.scrollIntoView = vi.fn()
    const onClose = vi.fn()
    const onSuccess = vi.fn()

    render(<SynastryAddSheet open={true} onClose={onClose} onSuccess={onSuccess} />)

    fireEvent.change(screen.getByLabelText(/Имя/i), { target: { value: "Ирина" } })
    fireEvent.change(screen.getByLabelText(/Дата рождения/i), { target: { value: "1992-05-20" } })

    // Open CityPicker suggestions and select Moscow from popular list
    const cityInput = screen.getByPlaceholderText(/Москва/i)
    fireEvent.focus(cityInput)
    const popularCityBtn = await screen.findByRole("button", { name: "Москва" })
    fireEvent.click(popularCityBtn)

    const submitBtn = screen.getByRole("button", { name: /Добавить и рассчитать/i })
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(createSynastryPartner).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Ирина",
          birthDate: "1992-05-20",
          birthCity: "Москва, Россия",
          birthLat: 55.7558,
          birthLon: 37.6173,
          birthTz: "Europe/Moscow",
        })
      )
      expect(onSuccess).toHaveBeenCalledWith("partner-123")
      expect(onClose).toHaveBeenCalled()
    })
  })
})
