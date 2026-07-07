import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { AccessInfo } from '@/lib/access'

const { mockGetDayStatus } = vi.hoisted(() => ({
  mockGetDayStatus: vi.fn(),
}))

vi.mock('@/lib/api/calendar', () => ({
  getDayStatus: mockGetDayStatus,
}))

vi.mock('@/lib/log', () => ({
  logEvent: vi.fn(),
}))

import { WeekStrip } from '@/components/today/week-strip'

const fullAccess: AccessInfo = {
  state: 'subscription',
  hasAccess: true,
  accessStart: null,
  accessEnd: null,
  daysLeft: 0,
}

describe('WeekStrip', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders missing backend status as unavailable instead of even', async () => {
    mockGetDayStatus.mockResolvedValue(null)

    render(
      <WeekStrip
        selectedDate={new Date('2026-07-07T12:00:00Z')}
        access={fullAccess}
      />,
    )

    await waitFor(() => expect(mockGetDayStatus).toHaveBeenCalledTimes(7))

    const buttons = screen.getAllByRole('button')
    expect(buttons[0].getAttribute('aria-label')).toContain('статус недоступен')
    expect(buttons[0].getAttribute('aria-label')).not.toContain('ровный день')
  })

  it('renders failed status requests as unavailable instead of even', async () => {
    mockGetDayStatus.mockRejectedValue(new Error('network down'))

    render(
      <WeekStrip
        selectedDate={new Date('2026-07-07T12:00:00Z')}
        access={fullAccess}
      />,
    )

    await waitFor(() => expect(mockGetDayStatus).toHaveBeenCalledTimes(7))

    const buttons = screen.getAllByRole('button')
    expect(buttons[0].getAttribute('aria-label')).toContain('статус недоступен')
    expect(buttons[0].getAttribute('aria-label')).not.toContain('ровный день')
  })
})
