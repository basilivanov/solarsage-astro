import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const { createCheckin, getCheckin, getYesterdayCheckin, push, toast } = vi.hoisted(() => ({
  createCheckin: vi.fn(),
  getCheckin: vi.fn(),
  getYesterdayCheckin: vi.fn(),
  push: vi.fn(),
  toast: vi.fn(),
}))

vi.mock("@/lib/api/checkin", () => ({
  createCheckin,
  getCheckin,
  getYesterdayCheckin,
}))

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast }),
}))

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push }),
}))

import { CheckinScreen } from "@/components/checkin/checkin-screen"
import { YesterdayEchoLoader } from "@/components/checkin/yesterday-echo"

describe("CheckinScreen", () => {
  beforeEach(() => {
    vi.clearAllMocks()
    getCheckin.mockResolvedValue(null)
    getYesterdayCheckin.mockResolvedValue({
      hadCheckin: false,
      checkin: null,
    })
    createCheckin.mockResolvedValue({
      id: 9,
      targetDate: "2026-07-06",
      mood: 5,
      accuracy: 3,
      energy: 4,
      tags: [],
      note: null,
      streak: 3,
      filledAt: "2026-07-06T20:00:00Z",
      createdAt: "2026-07-06T20:00:00Z",
    })
  })

  it("submits the three-tap numeric contract through the real API client", async () => {
    const onComplete = vi.fn()
    render(
      <CheckinScreen
        targetDate="2026-07-06"
        onComplete={onComplete}
      />,
    )

    await screen.findByTestId("mood-5")
    expect(screen.getByTestId("checkin-screen").getAttribute("data-state")).toBe("ready")
    expect(screen.getAllByRole("checkbox")).toHaveLength(12)
    fireEvent.click(screen.getByTestId("mood-5"))
    fireEvent.click(screen.getByTestId("energy-4"))
    fireEvent.click(screen.getByTestId("accuracy-3"))

    await waitFor(() => {
      expect(createCheckin).toHaveBeenCalledWith({
        targetDate: "2026-07-06",
        mood: 5,
        accuracy: 3,
        energy: 4,
        tags: [],
        note: null,
      })
    })

    // Post-submit confirmation screen displayed
    const postSubmit = await screen.findByTestId("checkin-post-submit")
    expect(postSubmit).toBeDefined()
    expect(screen.getByTestId("checkin-screen").getAttribute("data-state")).toBe("ready")
    expect(screen.getByText("Спасибо за отклик!")).toBeDefined()
    expect(screen.getByText(/3 дня подряд/i)).toBeDefined()

    const doneBtn = screen.getByTestId("checkin-done-btn")
    fireEvent.click(doneBtn)

    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({ streak: 3 }),
    )
  })

  it("keeps the user on the form and surfaces real API errors", async () => {
    createCheckin.mockRejectedValue(new Error("Check-in unavailable"))
    render(<CheckinScreen targetDate="2026-07-06" />)

    await screen.findByTestId("mood-4")
    fireEvent.click(screen.getByTestId("mood-4"))
    fireEvent.click(screen.getByTestId("energy-3"))
    fireEvent.click(screen.getByTestId("accuracy-2"))

    await waitFor(() => {
      expect(toast).toHaveBeenCalledWith({
        description: "Check-in unavailable",
        variant: "destructive",
      })
    })
    expect(screen.getByTestId("checkin-screen")).toBeTruthy()
  })

  it("loads an existing target-date check-in before showing the form", async () => {
    getYesterdayCheckin.mockResolvedValue({
      targetDate: "2026-07-05",
      hadCheckin: true,
      checkin: {
        id: 11,
        targetDate: "2026-07-05",
        mood: 4,
        accuracy: 2,
        energy: 3,
        tags: ["calm"],
        note: "Existing note",
        streak: 2,
        filledAt: "2026-07-05T20:00:00Z",
        createdAt: "2026-07-05T20:00:00Z",
      },
      forecastAvailable: false,
      forecastRecap: null,
    })

    render(<CheckinScreen targetDate="2026-07-05" />)

    expect(screen.getByText("Загружаем оценку...")).toBeTruthy()
    expect(await screen.findByText("Оценка уже сохранена")).toBeTruthy()
    expect(getYesterdayCheckin).toHaveBeenCalled()
    expect(screen.getByText("Existing note")).toBeTruthy()
  })

  it("shows a real read error without falling back to an empty form", async () => {
    getYesterdayCheckin.mockRejectedValue(new Error("Read unavailable"))

    render(<CheckinScreen targetDate="2026-07-06" />)

    expect(await screen.findByText("Read unavailable")).toBeTruthy()
    expect(screen.queryByTestId("mood-5")).toBeNull()
  })

  it("loads yesterday echo and routes its empty CTA to yesterday semantics", async () => {
    render(<YesterdayEchoLoader />)

    expect(screen.getByText("Загружаем вчерашнюю оценку...")).toBeTruthy()
    fireEvent.click(await screen.findByText("Оценить"))

    expect(getYesterdayCheckin).toHaveBeenCalledTimes(1)
    expect(push).toHaveBeenCalledWith("/checkin?target=yesterday")
  })
})
