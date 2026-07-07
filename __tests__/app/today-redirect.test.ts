import { beforeEach, describe, expect, it, vi } from 'vitest'

const { mockRedirect } = vi.hoisted(() => ({
  mockRedirect: vi.fn(),
}))

vi.mock('next/navigation', () => ({
  redirect: mockRedirect,
}))

import TodayPage from '@/app/(grace)/today/page'

describe('/today route', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        date: '2026-07-07',
        headline: 'legacy payload should not render',
      }),
    })
  })

  it('redirects to the migrated real-data day route', async () => {
    await TodayPage()

    expect(mockRedirect).toHaveBeenCalledWith('/day/today')
  })
})
