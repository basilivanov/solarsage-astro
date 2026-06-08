import { describe, it, expect, vi, beforeEach } from 'vitest'

describe('onboarding-flow: timezone in API payload', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('sends timezone fields for all three locations', async () => {
    const birthCity = {
      name: 'Мончегорск',
      country: 'Россия',
      lat: 67.93972,
      lon: 32.87389,
      timezone: 'Europe/Moscow',
    }
    const currentCity = {
      name: 'Сочи',
      country: 'Россия',
      lat: 43.59699,
      lon: 39.72477,
      timezone: 'Europe/Moscow',
    }

    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        userId: 'test-id',
        birth: { birthday: '1990-01-01', birthTz: 'Europe/Moscow' },
        currentLocation: { city: 'Сочи, Россия', lat: 43.59699, lon: 39.72477, tz: 'Europe/Moscow' },
        birthdayLocation: { city: 'Сочи, Россия', lat: 43.59699, lon: 39.72477, tz: 'Europe/Moscow' },
      }),
    })
    global.fetch = fetchMock

    const { updateProfile } = await import('../../lib/api/profile')

    await updateProfile({
      birth: {
        birthday: '1990-06-15',
        birthTime: '14:30',
        birthCity: 'Мончегорск, Россия',
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

    expect(body.birth.birthTz).toBe('Europe/Moscow')
    expect(body.currentLocation.tz).toBe('Europe/Moscow')
    expect(body.birthdayLocation.tz).toBe('Europe/Moscow')
    expect(body.currentLocation.city).toBe('Сочи, Россия')
  })

  it('omits timezone when city has no timezone (undefined)', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        userId: 'test-id',
        birth: {},
        currentLocation: null,
        birthdayLocation: null,
      }),
    })
    global.fetch = fetchMock

    const { updateProfile } = await import('../../lib/api/profile')

    await updateProfile({
      birth: {
        birthday: '1990-01-01',
        birthTime: '12:00',
        birthCity: 'SomeCity',
        birthLat: 50.0,
        birthLon: 10.0,
      },
    })

    const call = fetchMock.mock.calls[0]
    const body = JSON.parse(call[1].body)
    expect(body.birth.birthTz).toBeUndefined()
  })
})