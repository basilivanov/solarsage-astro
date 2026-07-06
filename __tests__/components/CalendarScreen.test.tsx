import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import React from 'react'
import type { AccessInfo } from '@/lib/contracts/access'
import type { CalendarPayloadReadModel } from '@/lib/contracts/calendar'

const { mockGetMonthCalendar, mockGetMonthStatuses } = vi.hoisted(() => ({
  mockGetMonthCalendar: vi.fn(),
  mockGetMonthStatuses: vi.fn(),
}))

vi.mock('@/lib/api/calendar', () => ({
  getMonthCalendar: mockGetMonthCalendar,
  getMonthStatuses: mockGetMonthStatuses,
}))

vi.mock('@/lib/today', () => ({
  TODAY: new Date('2026-07-06T12:00:00Z'),
  sameDay: (a: Date, b: Date) =>
    a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate(),
}))

import { CalendarScreen } from '@/components/calendar/calendar-screen'

const fullAccess: AccessInfo = {
  state: 'subscription',
  hasAccess: true,
  accessStart: null,
  accessEnd: null,
  daysLeft: 0,
}

function day(
  date: string,
  overrides: Partial<CalendarPayloadReadModel['days'][number]> = {},
): CalendarPayloadReadModel['days'][number] {
  const parsed = new Date(`${date}T12:00:00Z`)
  return {
    date,
    dayNumber: parsed.getUTCDate(),
    isCurrentMonth: date.startsWith('2026-07'),
    isToday: date === '2026-07-06',
    disabled: false,
    dayStatus: 'steady',
    access: {
      state: 'full',
      reason: 'active_subscription',
      referralDaysLeft: null,
      subscriptionActive: true,
      accessUntil: null,
    },
    lunar: {
      phase: null,
      illumination: null,
      moonSign: null,
      lunarDay: null,
      voidOfCourse: null,
    },
    ...overrides,
  }
}

function calendarPayload(overrides: Partial<CalendarPayloadReadModel> = {}): CalendarPayloadReadModel {
  return {
    meta: {
      schemaVersion: 'calendar/v1',
      contractVersion: 1,
      generatedAt: '2026-07-01T00:00:00Z',
    },
    month: '2026-07',
    title: 'Июль 2026',
    allowedRange: { from: '2026-06-01', to: '2026-08-31' },
    days: [
      day('2026-07-06', {
        dayStatus: 'supportive',
        lunar: {
          phase: 'Растущая Луна',
          illumination: 64,
          moonSign: 'Libra',
          lunarDay: 11,
          voidOfCourse: false,
        },
      }),
      day('2026-07-10', {
        dayStatus: 'tense',
        access: {
          state: 'locked',
          reason: 'outside_access_window',
          referralDaysLeft: 0,
          subscriptionActive: false,
          accessUntil: null,
        },
        lunar: {
          phase: 'Полнолуние',
          illumination: 99,
          moonSign: 'Capricorn',
          lunarDay: 15,
          voidOfCourse: true,
        },
      }),
    ],
    ...overrides,
  }
}

describe('CalendarScreen', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetMonthCalendar.mockResolvedValue(calendarPayload())
    mockGetMonthStatuses.mockResolvedValue({
      '2026-07-06': 'supportive',
      '2026-07-10': 'tense',
    })
  })

  it('uses full calendar payload per-day access and lunar fields from API view models', async () => {
    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))

    expect(screen.getByTestId('calendar-grid')).toBeTruthy()
    expect(screen.getByLabelText(/10 июля 2026, напряжённый, требуется подписка/i)).toBeTruthy()
    expect(screen.getByText('Полнолуние')).toBeTruthy()
    expect(screen.getByText('99%')).toBeTruthy()
    expect(screen.getByText('15 лунный день')).toBeTruthy()
    expect(screen.getByText(/без курса/i)).toBeTruthy()
  })

  it('shows lunar unavailable state when backend lunar fields are absent', async () => {
    mockGetMonthCalendar.mockResolvedValue(calendarPayload({
      days: [
        day('2026-07-06'),
        day('2026-07-10', {
          access: {
            state: 'locked',
            reason: 'outside_access_window',
            referralDaysLeft: 0,
            subscriptionActive: false,
            accessUntil: null,
          },
        }),
      ],
    }))

    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))
    expect(screen.getByTestId('lunar-calendar-unavailable').textContent).toContain('Лунные данные недоступны')
  })

  it('renders backend lunar values in moon mode instead of computing client-side phases', async () => {
    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))
    fireEvent.click(screen.getByRole('button', { name: 'Луна' }))

    expect(screen.getByLabelText(/10 июля 2026, Полнолуние, 15 лунный день, Луна без курса/i)).toBeTruthy()
  })

  it('does not synthesize missing month cells from local calendar math', async () => {
    mockGetMonthCalendar.mockResolvedValue(calendarPayload({
      days: [
        day('2026-07-06'),
        day('2026-07-10'),
      ],
    }))

    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))
    expect(screen.getByTestId('calendar-day-2026-07-06')).toBeTruthy()
    expect(screen.getByTestId('calendar-day-2026-07-10')).toBeTruthy()
    expect(screen.queryByTestId('calendar-day-2026-07-07')).toBeNull()
  })

  it('renders an explicit unavailable state when calendar payload fails', async () => {
    mockGetMonthCalendar.mockRejectedValue(new Error('calendar backend failed'))

    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))
    expect(screen.getByTestId('calendar-unavailable').textContent).toContain('Календарь недоступен')
    expect(screen.queryByTestId('calendar-grid')).toBeNull()
  })

  it('does not fall back to Gregorian date number when lunar day is absent', async () => {
    mockGetMonthCalendar.mockResolvedValue(calendarPayload({
      days: [
        day('2026-07-06', {
          lunar: {
            phase: 'Растущая Луна',
            illumination: 64,
            moonSign: 'Libra',
            lunarDay: null,
            voidOfCourse: false,
          },
        }),
      ],
    }))

    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))
    fireEvent.click(screen.getByRole('button', { name: 'Луна' }))

    expect(screen.getByTestId('calendar-moon-day-2026-07-06').textContent).toBe('—')
  })
})
