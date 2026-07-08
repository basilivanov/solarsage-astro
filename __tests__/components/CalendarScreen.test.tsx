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
      phaseIndex: null,
      phaseLabel: null,
      illumination: null,
      moonSign: null,
      moonSignLabel: null,
      lunarDay: null,
      voidOfCourse: null,
    } as any,
    ...overrides,
  }
}

function calendarPayload(overrides: Partial<CalendarPayloadReadModel> = {}): CalendarPayloadReadModel {
  return {
    meta: {
      schemaVersion: 'calendar/v1',
      contractVersion: 2,
      generatedAt: '2026-07-01T00:00:00Z',
    },
    month: '2026-07',
    title: 'July 2026',
    allowedRange: { from: '2026-06-01', to: '2026-08-31' },
    days: [
      day('2026-07-06', {
        dayStatus: 'supportive',
        lunar: {
          phase: 'waxing_gibbous',
          phaseIndex: 3,
          phaseLabel: 'раст. Луна',
          illumination: 64,
          moonSign: 'Libra',
          moonSignLabel: 'Весы',
          lunarDay: 11,
          voidOfCourse: false,
        } as any,
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
          phase: 'full_moon',
          phaseIndex: 4,
          phaseLabel: 'полнолуние',
          illumination: 99,
          moonSign: 'Capricorn',
          moonSignLabel: 'Козерог',
          lunarDay: 15,
          voidOfCourse: true,
        } as any,
      }),
    ],
    ...overrides,
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
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
    expect(screen.getAllByText('полнолуние').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByRole('button', { name: /полнолуние 10/i }))
    expect(screen.getAllByText('99%').length).toBeGreaterThan(0)
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

    expect(screen.getByLabelText(/10 июля 2026, полнолуние, 15 лунный день, Луна без курса/i)).toBeTruthy()
    expect(screen.getByTestId('calendar-moon-glyph-2026-07-10').textContent).toContain('🌕')
  })

  it('renders a compact current-month visual window from the backend three-month payload', async () => {
    mockGetMonthCalendar.mockResolvedValue(calendarPayload({
      days: [
        day('2026-06-01', { isCurrentMonth: false, disabled: true }),
        day('2026-06-29', { isCurrentMonth: false, disabled: true }),
        day('2026-06-30', { isCurrentMonth: false, disabled: true }),
        day('2026-07-10'),
        day('2026-08-01', { isCurrentMonth: false, disabled: true }),
        day('2026-08-02', { isCurrentMonth: false, disabled: true }),
        day('2026-08-31', { isCurrentMonth: false, disabled: true }),
      ],
    }))

    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))
    expect(screen.getByTestId('calendar-day-2026-07-10')).toBeTruthy()
    expect(screen.getByTestId('calendar-day-2026-06-29')).toBeTruthy()
    expect(screen.getByTestId('calendar-day-2026-08-02')).toBeTruthy()
    expect(screen.queryByTestId('calendar-day-2026-06-01')).toBeNull()
    expect(screen.queryByTestId('calendar-day-2026-08-31')).toBeNull()
  })

  it('uses Russian month title derived from payload month instead of backend English title', async () => {
    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))
    expect(screen.getByTestId('calendar-month-header').textContent).toBe('Июль 2026')
    expect(screen.queryByText('July 2026')).toBeNull()
  })

  it('selects a day locally and opens it only from the footer CTA', async () => {
    const onOpenDay = vi.fn()
    render(<CalendarScreen access={fullAccess} onOpenDay={onOpenDay} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))
    fireEvent.click(screen.getByTestId('calendar-day-2026-07-10'))

    expect(onOpenDay).not.toHaveBeenCalled()
    expect(screen.getByTestId('calendar-selected-summary').textContent).toContain('10 июля 2026')

    fireEvent.click(screen.getByRole('button', { name: /Открыть превью/i }))
    expect(onOpenDay).toHaveBeenCalledTimes(1)
    expect(onOpenDay.mock.calls[0][0]).toEqual(new Date(2026, 6, 10))
  })

  it('renders an explicit unavailable state when calendar payload fails', async () => {
    mockGetMonthCalendar.mockRejectedValue(new Error('calendar backend failed'))

    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))
    expect(screen.getByTestId('calendar-unavailable').textContent).toContain('Календарь недоступен')
    expect(screen.queryByTestId('calendar-grid')).toBeNull()
  })

  it('shows a real loading state while the first calendar request is in flight', async () => {
    const pending = deferred<CalendarPayloadReadModel>()
    mockGetMonthCalendar.mockReturnValue(pending.promise)

    render(<CalendarScreen access={fullAccess} />)

    expect(screen.getByTestId('calendar-loading').textContent).toContain('Загружаем календарь')
    expect(screen.queryByTestId('calendar-unavailable')).toBeNull()
    expect(screen.queryByTestId('calendar-grid')).toBeNull()

    pending.resolve(calendarPayload())
    await waitFor(() => expect(screen.getByTestId('calendar-grid')).toBeTruthy())
  })

  it('clears stale month days and shows loading while the next month request is pending', async () => {
    const nextMonthPending = deferred<CalendarPayloadReadModel>()
    mockGetMonthCalendar
      .mockResolvedValueOnce(calendarPayload())
      .mockReturnValueOnce(nextMonthPending.promise)

    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(screen.getByTestId('calendar-day-2026-07-06')).toBeTruthy())
    fireEvent.click(screen.getByRole('button', { name: 'Следующий месяц' }))

    expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 7)
    expect(screen.getByTestId('calendar-loading')).toBeTruthy()
    expect(screen.queryByTestId('calendar-day-2026-07-06')).toBeNull()
    expect(screen.queryByTestId('calendar-grid')).toBeNull()

    nextMonthPending.resolve(calendarPayload({
      month: '2026-08',
      title: 'Август 2026',
      days: [
        day('2026-08-03', {
          dayStatus: 'supportive',
          isCurrentMonth: true,
          isToday: false,
        }),
      ],
    }))

    await waitFor(() => expect(screen.getByTestId('calendar-day-2026-08-03')).toBeTruthy())
  })

  it('does not fall back to Gregorian date number when lunar day is absent', async () => {
    mockGetMonthCalendar.mockResolvedValue(calendarPayload({
      days: [
        day('2026-07-06', {
          lunar: {
            phase: 'waxing_gibbous',
            phaseIndex: 3,
            phaseLabel: 'раст. Луна',
            illumination: 64,
            moonSign: 'Libra',
            moonSignLabel: 'Весы',
            lunarDay: null,
            voidOfCourse: false,
          } as any,
        }),
      ],
    }))

    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))
    fireEvent.click(screen.getByRole('button', { name: 'Луна' }))

    expect(screen.getByTestId('calendar-moon-day-2026-07-06').textContent).toBe('—')
  })

  it('renders unknown backend day status as unavailable instead of synthesizing an even day', async () => {
    mockGetMonthCalendar.mockResolvedValue(calendarPayload({
      days: [
        day('2026-07-06', {
          dayStatus: null,
        }),
      ],
    }))

    render(<CalendarScreen access={fullAccess} />)

    await waitFor(() => expect(mockGetMonthCalendar).toHaveBeenCalledWith(2026, 6))

    expect(screen.getByLabelText(/6 июля 2026, статус недоступен/i)).toBeTruthy()
    expect(screen.queryByText('ровный')).toBeNull()
    expect(screen.getByText('Статус недоступен')).toBeTruthy()
  })
})
