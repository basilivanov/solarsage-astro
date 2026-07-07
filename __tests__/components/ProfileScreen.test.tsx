import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import type { Profile } from "@/lib/profile"

let loaded = false
let mockError: string | null = null

vi.mock("@/hooks/use-profile", () => ({
  useProfile: () => ({
    profile: {
      firstName: "",
      birthDate: { day: "", month: "", year: "" },
      birthTime: { hours: "", minutes: "", unknown: true },
      birthPlace: "",
      currentCity: "",
      birthdayCity: "",
      birthLocation: null,
      currentLocation: null,
      birthdayLocation: null,
      gender: null,
      isOnboarded: false,
      sameAsBirth: false,
      birthdaySameAsCurrent: false,
    } satisfies Profile,
    update: vi.fn(),
    loaded,
    saving: false,
    error: mockError,
  }),
}))

vi.mock("@/hooks/use-telegram-user", () => ({
  useTelegramUser: () => null,
}))

vi.mock("@/components/profile/edit-sheet", () => ({
  EditSheet: () => <div role="dialog">edit sheet</div>,
}))
vi.mock("@/components/profile/access-card", () => ({
  AccessCard: () => <div />,
}))
vi.mock("@/components/profile/referral-card", () => ({
  ReferralCard: () => <div />,
}))
vi.mock("@/components/profile/horary-card", () => ({
  HoraryCard: () => <div />,
}))
vi.mock("@/components/profile/checkin-statistics", () => ({
  CheckinStatistics: () => <section>Статистика оценок</section>,
}))

import { ProfileScreen } from "@/components/profile/profile-screen"

const access = {
  state: "none" as const,
  hasAccess: false,
  accessStart: null,
  accessEnd: null,
  daysLeft: 0,
}

const profileMeta = {
  horary: {
    weeklyFreeAvailable: false,
    weeklyFreeExpiresAt: null,
    nextWeeklyFreeAt: null,
    bonusCredits: 0,
    paidCredits: 0,
    canPurchase: true,
  },
  referral: { count: 0, bonusDays: 0, rewardDays: 14, inviteUrl: "" },
}

describe("ProfileScreen hydration gate", () => {
  it("does not open profile editors before backend hydration completes", () => {
    loaded = false
    mockError = null
    loaded = false
    render(
      <ProfileScreen
        access={access}
        currentState="none"
        profileMeta={profileMeta}
      />,
    )

    fireEvent.click(screen.getByText("Дата рождения"))

    expect(screen.queryByRole("dialog")).toBeNull()
    expect(screen.getByText("Загружаем данные профиля...")).toBeTruthy()
  })

  it("opens profile editors after backend hydration completes", () => {
    loaded = true
    render(
      <ProfileScreen
        access={access}
        currentState="none"
        profileMeta={profileMeta}
      />,
    )

    fireEvent.click(screen.getByText("Дата рождения"))

    expect(screen.getByRole("dialog")).toBeTruthy()
  })

  it("includes check-in statistics sourced by the real metrics component", () => {
    loaded = true
    render(
      <ProfileScreen
        access={access}
        currentState="none"
        profileMeta={profileMeta}
      />,
    )

    expect(screen.getByText("Статистика оценок")).toBeTruthy()
  })

  it("root data-state is loading before profile hydration", () => {
    loaded = false
    mockError = null
    render(
      <ProfileScreen
        access={access}
        currentState="none"
        profileMeta={profileMeta}
      />,
    )

    expect(screen.getByTestId("profile-screen").getAttribute("data-state")).toBe("loading")
  })

  it("root data-state is error when hydration fails", () => {
    loaded = false
    mockError = "Network error"
    render(
      <ProfileScreen
        access={access}
        currentState="none"
        profileMeta={profileMeta}
      />,
    )

    expect(screen.getByTestId("profile-screen").getAttribute("data-state")).toBe("error")
  })

  it("root data-state is ready after hydration even when save error exists", () => {
    loaded = true
    mockError = "Save failed"
    render(
      <ProfileScreen
        access={access}
        currentState="none"
        profileMeta={profileMeta}
      />,
    )

    // Hydration succeeded → data-state="ready" regardless of save error
    expect(screen.getByTestId("profile-screen").getAttribute("data-state")).toBe("ready")
  })

  it("loading hint has role=status", () => {
    loaded = false
    mockError = null
    render(
      <ProfileScreen
        access={access}
        currentState="none"
        profileMeta={profileMeta}
      />,
    )

    expect(screen.getByText("Загружаем данные профиля...").getAttribute("role")).toBe("status")
  })

  it("load error has role=alert", () => {
    loaded = false
    mockError = "Network error"
    render(
      <ProfileScreen
        access={access}
        currentState="none"
        profileMeta={profileMeta}
      />,
    )

    const el = screen.getByText(/Не удалось загрузить профиль/)
    expect(el.getAttribute("role")).toBe("alert")
  })
})
