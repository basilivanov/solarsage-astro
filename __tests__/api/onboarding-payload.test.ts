// ############################################################################
// AI_HEADER: MODULE_API_ONBOARDING_PAYLOAD_TEST
// ROLE: Unit tests for onboarding payload timezone formatting in lib/api/profile.ts
// DEPENDENCIES: vitest, lib/api/profile
// GRACE_ANCHORS: [ONBOARDING_PAYLOAD_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-ONBOARDING-PAYLOAD
// purpose: Validate profile update payload generation for onboarding timezones and contract-valid ProfileRead response parsing.
// owns:
//   - __tests__/api/onboarding-payload.test.ts
// inputs: mock fetch responses and ProfileWrite payloads
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-PROFILE (updateProfile)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-ONBOARDING-PAYLOAD

// START_MODULE_MAP: M-TESTS-ONBOARDING-PAYLOAD
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - TIMEZONE_TESTS: test timezone presence and omission in ProfileWrite PUT requests
// owned_tests:
//   - __tests__/api/onboarding-payload.test.ts
// END_MODULE_MAP: M-TESTS-ONBOARDING-PAYLOAD

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

const VALID_PROFILE_READ = {
  userId: "11111111-1111-1111-1111-111111111111",
  birth: {
    birthday: "1990-01-01",
    birthTime: "14:30",
    birthCity: "Мончегорск, Россия",
    birthLat: 67.93972,
    birthLon: 32.87389,
    birthTz: "Europe/Moscow",
  },
  currentLocation: { city: "Сочи, Россия", lat: 43.59699, lon: 39.72477, tz: "Europe/Moscow" },
  birthdayLocation: { city: "Сочи, Россия", lat: 43.59699, lon: 39.72477, tz: "Europe/Moscow" },
}

describe("onboarding-flow: timezone in API payload", () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it("sends timezone fields for all three locations", async () => {
    const birthCity = {
      name: "Мончегорск",
      country: "Россия",
      lat: 67.93972,
      lon: 32.87389,
      timezone: "Europe/Moscow",
    }
    const currentCity = {
      name: "Сочи",
      country: "Россия",
      lat: 43.59699,
      lon: 39.72477,
      timezone: "Europe/Moscow",
    }

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => VALID_PROFILE_READ,
    })
    vi.stubGlobal("fetch", fetchMock)

    const { updateProfile } = await import("../../lib/api/profile")

    await updateProfile({
      birth: {
        birthday: "1990-06-15",
        birthTime: "14:30",
        birthCity: "Мончегорск, Россия",
        birthLat: birthCity.lat,
        birthLon: birthCity.lon,
        birthTz: birthCity.timezone,
      },
      currentLocation: {
        city: `${currentCity.name}, ${currentCity.country}`,
        lat: currentCity.lat,
        lon: currentCity.lon,
        tz: currentCity.timezone,
      },
      birthdayLocation: {
        city: `${currentCity.name}, ${currentCity.country}`,
        lat: currentCity.lat,
        lon: currentCity.lon,
        tz: currentCity.timezone,
      },
    })

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const call = fetchMock.mock.calls[0]
    const body = JSON.parse(call[1].body)

    expect(body.birth.birthTz).toBe("Europe/Moscow")
    expect(body.currentLocation.tz).toBe("Europe/Moscow")
    expect(body.birthdayLocation.tz).toBe("Europe/Moscow")
    expect(body.currentLocation.city).toBe("Сочи, Россия")
  })

  it("omits timezone when city has no timezone (undefined)", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...VALID_PROFILE_READ,
        currentLocation: null,
        birthdayLocation: null,
      }),
    })
    vi.stubGlobal("fetch", fetchMock)

    const { updateProfile } = await import("../../lib/api/profile")

    await updateProfile({
      birth: {
        birthday: "1990-01-01",
        birthTime: "12:00",
        birthCity: "SomeCity",
        birthLat: 50.0,
        birthLon: 10.0,
      },
    })

    const call = fetchMock.mock.calls[0]
    const body = JSON.parse(call[1].body)
    expect(body.birth.birthTz).toBeUndefined()
  })
})
