// ############################################################################
// AI_HEADER: TEST_CITY_PICKER — search error state and popular cities contract
// ROLE: Proves CityPicker surfaces an accessible error on search failure and
//       keeps the popular cities list intact.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-CITY-PICKER
// purpose: Verify that a failed city search shows a role="alert" message
//   (not a silent empty list), a successful search hides it, and the popular
//   cities catalog is untouched by the error path.
// owns:
//   - __tests__/components/CityPicker.test.tsx
// inputs: mocked lib/api/cities searchCitiesAsync
// outputs: vitest assertions
// dependencies: vitest, @testing-library/react
// side_effects: none
// emitted_logs: none
// invariants:
//   - popular cities render when input is empty; error appears only after a
//     failed search with non-empty input; no unhandled promise rejections
// failure_policy: assertion failure on contract violation
// END_MODULE_CONTRACT: M-TEST-CITY-PICKER

import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, fireEvent, act } from "@testing-library/react"

const { mockSearch } = vi.hoisted(() => ({ mockSearch: vi.fn() }))

vi.mock("@/lib/api/cities", () => ({
  searchCitiesAsync: mockSearch,
  getPopularCities: () => [
    { name: "Москва", country: "Россия", lat: 55.75, lon: 37.62, timezone: "Europe/Moscow" },
    { name: "Санкт-Петербург", country: "Россия", lat: 59.94, lon: 30.31, timezone: "Europe/Moscow" },
  ],
}))

vi.mock("@/lib/api/geo", () => ({
  getTimezone: vi.fn().mockResolvedValue({ timezone_id: "Europe/Moscow" }),
}))

vi.mock("@/lib/log", () => ({
  logEvent: vi.fn(),
}))

import { CityPicker } from "@/components/onboarding/city-picker"

describe("CityPicker", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers()
    // jsdom does not implement scrollIntoView; stub it for the focus handler.
    Element.prototype.scrollIntoView = vi.fn()
  })

  it("shows an accessible alert when the search fails (not a silent empty list)", async () => {
    mockSearch.mockRejectedValue(new Error("geo down"))
    render(<CityPicker value={null} onChange={() => {}} />)

    const input = screen.getByRole("textbox")
    fireEvent.focus(input)
    fireEvent.change(input, { target: { value: "Мос" } })

    await act(async () => {
      await new Promise((r) => setTimeout(r, 450)) // debounce 300ms + settle
    })

    expect(mockSearch).toHaveBeenCalled()
    expect(screen.getByRole("alert").textContent).toContain("Не получилось найти город")
  })

  it("hides the alert again after a successful retry", async () => {
    mockSearch
      .mockRejectedValueOnce(new Error("geo down"))
      .mockResolvedValue([
        { name: "Москва", country: "Россия", lat: 55.75, lon: 37.62, timezone: "Europe/Moscow" },
      ])
    render(<CityPicker value={null} onChange={() => {}} />)

    const input = screen.getByRole("textbox")
    fireEvent.focus(input)
    fireEvent.change(input, { target: { value: "Мос" } })
    await act(async () => { await new Promise((r) => setTimeout(r, 450)) })
    expect(screen.getByRole("alert")).not.toBeNull()

    fireEvent.change(input, { target: { value: "Моск" } })
    await act(async () => { await new Promise((r) => setTimeout(r, 450)) })
    expect(screen.queryByRole("alert")).toBeNull()
    expect(screen.getByText("Москва")).not.toBeNull()
  })

  it("keeps popular cities when the input is empty (error path untouched)", () => {
    render(<CityPicker value={null} onChange={() => {}} />)
    expect(screen.getByText("Популярные")).not.toBeNull()
    expect(screen.getByRole("button", { name: "Москва" })).not.toBeNull()
    expect(screen.getByRole("button", { name: "Санкт-Петербург" })).not.toBeNull()
    expect(screen.queryByRole("alert")).toBeNull()
  })
})
