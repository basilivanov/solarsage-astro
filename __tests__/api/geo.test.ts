import { describe, it, expect, vi, beforeEach } from 'vitest'
import { searchCities, getTimezone } from '../../lib/api/geo'

describe('searchCities', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns suggestions with timezone_id', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: '1',
          name: 'Moscow',
          admin1: 'Moscow',
          country: 'Russia',
          lat: 55.75,
          lon: 37.62,
          label: 'Moscow, Russia',
          timezone_id: 'Europe/Moscow',
        },
      ],
    })

    const result = await searchCities('Moscow', 8)
    expect(result).toHaveLength(1)
    expect(result[0].timezone_id).toBe('Europe/Moscow')
  })

  it('returns undefined timezone_id when not provided', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: '2',
          name: 'SmallTown',
          admin1: null,
          country: 'XX',
          lat: 10.0,
          lon: 20.0,
          label: 'SmallTown, XX',
        },
      ],
    })

    const result = await searchCities('SmallTown', 8)
    expect(result).toHaveLength(1)
    expect(result[0].timezone_id).toBeUndefined()
  })
})

describe('getTimezone', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns timezone data for valid coordinates', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        timezone_id: 'Europe/Moscow',
        gmt_offset: 3.0,
        dst_offset: 3.0,
        raw_offset: 3.0,
      }),
    })

    const result = await getTimezone(55.75, 37.62)
    expect(result.timezone_id).toBe('Europe/Moscow')
    expect(result.gmt_offset).toBe(3.0)
  })

  it('throws on HTTP error', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
    })

    await expect(getTimezone(55.75, 37.62)).rejects.toThrow()
  })
})