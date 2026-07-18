// ############################################################################
// AI_HEADER: TEST_WEEK_STRIP — intent-based day-status warmup contract tests
// ROLE: Proves zero mount-time batch status loads and idempotent user-intent warmup.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-WEEK-STRIP
// purpose: Verify WeekStrip issues no day-status requests on mount, exactly one
//   on first pointer/focus intent, never duplicates hover+focus, and never
//   prefetches locked or active days.
// owns:
//   - __tests__/components/WeekStrip.test.tsx
// inputs: rendered WeekStrip with mocked getDayStatus
// outputs: vitest assertions
// dependencies: @testing-library/react, vitest
// side_effects: none
// emitted_logs: none
// invariants:
//   - Mount performs 0 status calls; first intent performs exactly 1; repeated
//     hover and focus keep the count at 1; locked/active days perform 0.
// failure_policy: assertion failure on any contract violation.
// END_MODULE_CONTRACT: M-TEST-WEEK-STRIP

import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

const lockedAccess: AccessInfo = {
  state: 'none',
  hasAccess: false,
  accessStart: null,
  accessEnd: null,
  daysLeft: 0,
}

const SELECTED = new Date('2026-07-07T12:00:00Z')

function inactiveDayButtonIndex(): number {
  // The selected day is at monday-first index 1 (2026-07-07 is Tuesday);
  // index 0 (Monday) is an inactive accessible day.
  return 0
}

describe('WeekStrip intent warmup', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('performs zero day-status calls on mount', () => {
    mockGetDayStatus.mockResolvedValue('ровный')
    render(<WeekStrip selectedDate={SELECTED} access={fullAccess} />)
    expect(mockGetDayStatus).not.toHaveBeenCalled()
  })

  it('warms exactly one status on first pointer intent and applies it', async () => {
    mockGetDayStatus.mockResolvedValue('ровный')
    render(<WeekStrip selectedDate={SELECTED} access={fullAccess} />)
    const buttons = screen.getAllByRole('button')
    fireEvent.pointerEnter(buttons[inactiveDayButtonIndex()])
    await waitFor(() => expect(mockGetDayStatus).toHaveBeenCalledTimes(1))
    await waitFor(() =>
      expect(buttons[inactiveDayButtonIndex()].getAttribute('aria-label')).toContain('ровный день'),
    )
  })

  it('does not duplicate on repeated hover and keyboard focus for the same day', async () => {
    mockGetDayStatus.mockResolvedValue('ровный')
    render(<WeekStrip selectedDate={SELECTED} access={fullAccess} />)
    const buttons = screen.getAllByRole('button')
    const dayButton = buttons[inactiveDayButtonIndex()]
    fireEvent.pointerEnter(dayButton)
    await waitFor(() => expect(mockGetDayStatus).toHaveBeenCalledTimes(1))
    fireEvent.pointerEnter(dayButton)
    fireEvent.focus(dayButton)
    fireEvent.pointerEnter(dayButton)
    fireEvent.focus(dayButton)
    expect(mockGetDayStatus).toHaveBeenCalledTimes(1)
  })

  it('does not duplicate when two different days receive intent', async () => {
    mockGetDayStatus.mockResolvedValue('ровный')
    render(<WeekStrip selectedDate={SELECTED} access={fullAccess} />)
    const buttons = screen.getAllByRole('button')
    fireEvent.pointerEnter(buttons[0])
    fireEvent.pointerEnter(buttons[2])
    await waitFor(() => expect(mockGetDayStatus).toHaveBeenCalledTimes(2))
  })

  it('never prefetches the active (selected) day', () => {
    mockGetDayStatus.mockResolvedValue('ровный')
    render(<WeekStrip selectedDate={SELECTED} access={fullAccess} />)
    const buttons = screen.getAllByRole('button')
    const activeButton = buttons.find((b) => b.getAttribute('aria-pressed') === 'true')!
    fireEvent.pointerEnter(activeButton)
    fireEvent.focus(activeButton)
    expect(mockGetDayStatus).not.toHaveBeenCalled()
  })

  it('never prefetches locked days', () => {
    mockGetDayStatus.mockResolvedValue('ровный')
    render(<WeekStrip selectedDate={SELECTED} access={lockedAccess} />)
    const buttons = screen.getAllByRole('button')
    for (const b of buttons) {
      fireEvent.pointerEnter(b)
      fireEvent.focus(b)
    }
    expect(mockGetDayStatus).not.toHaveBeenCalled()
  })

  it('disables warmup entirely when disableRemoteStatusFetch is set', () => {
    mockGetDayStatus.mockResolvedValue('ровный')
    render(<WeekStrip selectedDate={SELECTED} access={fullAccess} disableRemoteStatusFetch />)
    const buttons = screen.getAllByRole('button')
    for (const b of buttons) {
      fireEvent.pointerEnter(b)
      fireEvent.focus(b)
    }
    expect(mockGetDayStatus).not.toHaveBeenCalled()
  })

  it('marks a failed warmup as status unavailable for that day only', async () => {
    mockGetDayStatus.mockRejectedValue(new Error('network down'))
    render(<WeekStrip selectedDate={SELECTED} access={fullAccess} />)
    const buttons = screen.getAllByRole('button')
    fireEvent.pointerEnter(buttons[inactiveDayButtonIndex()])
    await waitFor(() => expect(mockGetDayStatus).toHaveBeenCalledTimes(1))
    await waitFor(() =>
      expect(buttons[inactiveDayButtonIndex()].getAttribute('aria-label')).toContain('статус недоступен'),
    )
  })
})
