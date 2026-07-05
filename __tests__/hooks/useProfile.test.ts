// ############################################################################
// AI_HEADER: MODULE_HOOKS_USEPROFILE_TEST
// ROLE: Unit tests for useProfile.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
import { beforeEach, describe, expect, it, vi } from "vitest"
import { act, renderHook, waitFor } from "@testing-library/react"

const { getProfile, updateProfile } = vi.hoisted(() => ({
  getProfile: vi.fn(),
  updateProfile: vi.fn(),
}))
const profileStore = new Map<string, string>()

vi.mock("@/lib/api/profile", () => ({
  getProfile,
  updateProfile,
}))

import { EMPTY_PROFILE, type Profile } from "@/lib/profile"
import { useProfile } from "@/hooks/use-profile"

const apiProfile = {
  userId: "64c31e3a-a7db-4a35-b12a-cd75fc8156d6",
  firstName: "Ada",
  gender: "female" as const,
  isOnboarded: true,
  birth: {
    birthday: "1985-12-10",
    birthTime: "12:05:00",
    birthCity: "London, UK",
    birthLat: 51.5074,
    birthLon: -0.1278,
    birthTz: "Europe/London",
  },
  currentLocation: {
    city: "Lisbon, Portugal",
    lat: 38.7223,
    lon: -9.1393,
    tz: "Europe/Lisbon",
  },
  birthdayLocation: {
    city: "Tokyo, Japan",
    lat: 35.6762,
    lon: 139.6503,
    tz: "Asia/Tokyo",
  },
}

beforeEach(() => {
  vi.clearAllMocks()
  profileStore.clear()
  getProfile.mockResolvedValue(apiProfile)
  updateProfile.mockResolvedValue(apiProfile)
  Object.defineProperty(window, "localStorage", {
    value: {
      getItem: vi.fn((key: string) => profileStore.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => profileStore.set(key, value)),
      removeItem: vi.fn((key: string) => profileStore.delete(key)),
    },
    writable: true,
  })
})

describe("useProfile", () => {
  it("loads the backend profile on mount and maps it into the UI model", async () => {
    const { result } = renderHook(() => useProfile())

    expect(getProfile).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(result.current.loaded).toBe(true))

    expect(result.current.profile).toMatchObject({
      firstName: "Ada",
      gender: "female",
      birthDate: { day: "10", month: "12", year: "1985" },
      birthTime: { hours: "12", minutes: "05", unknown: false },
      birthPlace: "London, UK",
      currentCity: "Lisbon, Portugal",
      birthdayCity: "Tokyo, Japan",
      birthLocation: {
        city: "London, UK",
        lat: 51.5074,
        lon: -0.1278,
        timezone: "Europe/London",
      },
      currentLocation: {
        city: "Lisbon, Portugal",
        lat: 38.7223,
        lon: -9.1393,
        timezone: "Europe/Lisbon",
      },
      birthdayLocation: {
        city: "Tokyo, Japan",
        lat: 35.6762,
        lon: 139.6503,
        timezone: "Asia/Tokyo",
      },
    })
  })

  it("uses an empty profile instead of fake Kyiv or Lisbon defaults", async () => {
    getProfile.mockResolvedValue({
      ...apiProfile,
      firstName: null,
      gender: null,
      isOnboarded: false,
      birth: {},
      currentLocation: null,
      birthdayLocation: null,
    })

    const { result } = renderHook(() => useProfile())
    await waitFor(() => expect(result.current.loaded).toBe(true))

    expect(result.current.profile).toEqual(EMPTY_PROFILE)
    expect(JSON.stringify(result.current.profile)).not.toContain("Киев")
    expect(JSON.stringify(result.current.profile)).not.toContain("Лиссабон")
  })

  it("uses only an API-sourced cache while the backend request is pending", () => {
    const cached: Profile = {
      ...EMPTY_PROFILE,
      firstName: "Cached",
      birthPlace: "Berlin, Germany",
      birthLocation: {
        city: "Berlin, Germany",
        lat: 52.52,
        lon: 13.405,
        timezone: "Europe/Berlin",
      },
    }
    profileStore.set(
      "lumen:profile",
      JSON.stringify({ source: "api", profile: cached }),
    )
    getProfile.mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useProfile())

    expect(result.current.profile.birthPlace).toBe("Berlin, Germany")
    expect(result.current.loaded).toBe(false)
  })

  it("ignores legacy unmarked localStorage profile data", () => {
    profileStore.set(
      "lumen:profile",
      JSON.stringify({ ...EMPTY_PROFILE, birthPlace: "Киев, Украина" }),
    )
    getProfile.mockReturnValue(new Promise(() => {}))

    const { result } = renderHook(() => useProfile())

    expect(result.current.profile).toEqual(EMPTY_PROFILE)
  })

  it("persists edits through PUT and preserves location metadata", async () => {
    updateProfile.mockImplementation(async (payload) => ({
      ...apiProfile,
      birth: {
        ...apiProfile.birth,
        birthday: payload.birth.birthday,
      },
    }))
    const { result } = renderHook(() => useProfile())
    await waitFor(() => expect(result.current.loaded).toBe(true))

    await act(async () => {
      await result.current.update({
        birthDate: { day: "11", month: "12", year: "1985" },
      })
    })

    expect(updateProfile).toHaveBeenCalledWith({
      firstName: "Ada",
      gender: "female",
      birth: {
        birthday: "1985-12-11",
        birthTime: "12:05:00",
        birthCity: "London, UK",
        birthLat: 51.5074,
        birthLon: -0.1278,
        birthTz: "Europe/London",
      },
      currentLocation: {
        city: "Lisbon, Portugal",
        lat: 38.7223,
        lon: -9.1393,
        tz: "Europe/Lisbon",
      },
      birthdayLocation: {
        city: "Tokyo, Japan",
        lat: 35.6762,
        lon: 139.6503,
        tz: "Asia/Tokyo",
      },
    })
    expect(result.current.profile.birthDate.day).toBe("11")
  })

  it("surfaces backend validation errors without closing over a fake success", async () => {
    updateProfile.mockRejectedValue(new Error("birthTz is invalid"))
    const { result } = renderHook(() => useProfile())
    await waitFor(() => expect(result.current.loaded).toBe(true))

    let thrown: unknown
    await act(async () => {
      try {
        await result.current.update({
          birthDate: { day: "11", month: "12", year: "1985" },
        })
      } catch (error) {
        thrown = error
      }
    })

    expect(thrown).toEqual(new Error("birthTz is invalid"))
    expect(result.current.error).toBe("birthTz is invalid")
    expect(result.current.profile.birthDate.day).toBe("10")
  })
})
