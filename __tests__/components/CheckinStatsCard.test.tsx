import { render, screen, waitFor } from "@testing-library/react"
import { describe, expect, it, vi } from "vitest"
import { CheckinStatsCard } from "@/components/profile/checkin-stats-card"

vi.mock("@/lib/api/checkin", () => ({
  getCheckinMetrics: vi.fn(),
}))

import { getCheckinMetrics } from "@/lib/api/checkin"

describe("CheckinStatsCard", () => {
  it("renders streak metrics and milestone badges", async () => {
    vi.mocked(getCheckinMetrics).mockResolvedValue({
      totalCheckins: 21,
      currentStreak: 5,
      longestStreak: 12,
      averageMood: 3.4,
      averageEnergy: 3.1,
      averageAccuracy: 2.2,
      moodDistribution: {},
      accuracyDistribution: {},
      tagFrequency: {},
    })

    render(<CheckinStatsCard />)

    await waitFor(() => {
      expect(screen.getByTestId("checkin-stats-card")).toBeDefined()
      expect(screen.getByText(/5/)).toBeDefined()
      expect(screen.getByText(/12/)).toBeDefined()
      expect(screen.getByText(/21/)).toBeDefined()
    })
    expect(screen.getByText("Неделя")).toBeDefined()
    expect(screen.getByText("Месяц")).toBeDefined()
  })
})
