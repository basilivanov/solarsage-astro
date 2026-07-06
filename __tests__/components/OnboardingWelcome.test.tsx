import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/lib/api/profile", () => ({
  updateProfile: vi.fn(),
}))

vi.mock("@/lib/log", () => ({
  logEvent: vi.fn(),
}))

import { OnboardingFlow } from "@/components/onboarding/onboarding-flow"

describe("OnboardingFlow welcome", () => {
  it("does not offer a completion path that bypasses profile persistence", () => {
    render(<OnboardingFlow onComplete={vi.fn()} />)

    expect(
      screen.queryByText("Пропустить и сразу открыть приложение"),
    ).toBeNull()
  })
})
