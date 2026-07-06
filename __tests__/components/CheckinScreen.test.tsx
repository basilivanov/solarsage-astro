import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

const { createCheckin, toast } = vi.hoisted(() => ({
  createCheckin: vi.fn(),
  toast: vi.fn(),
}))

vi.mock("@/lib/api/checkin", () => ({
  createCheckin,
}))

vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ toast }),
}))

import { CheckinScreen } from "@/components/checkin/checkin-screen"

describe("CheckinScreen", () => {
  beforeEach(() => {
    vi.clearAllMocks()
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
    expect(onComplete).toHaveBeenCalledWith(
      expect.objectContaining({ streak: 3 }),
    )
  })

  it("keeps the user on the form and surfaces real API errors", async () => {
    createCheckin.mockRejectedValue(new Error("Check-in unavailable"))
    render(<CheckinScreen targetDate="2026-07-06" />)

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
})
