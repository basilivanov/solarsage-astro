import { describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen } from "@testing-library/react"
import type { Profile } from "@/lib/profile"

const update = vi.fn()
let loaded = false

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
    update,
    loaded,
    saving: false,
    error: null,
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
  referral: { count: 0, bonusDays: 0, rewardDays: 7, inviteUrl: "" },
}

describe("ProfileScreen hydration gate", () => {
  it("does not open profile editors before backend hydration completes", () => {
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
})
