// ############################################################################
// AI_HEADER: TEST_WEEK_STRIP — zero-remote week strip contract tests.
// ROLE: Proves WeekStrip never calls /api/day (mount/hover/focus) and that
//       click only invokes onSelect once — the component itself never fetches.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-WEEK-STRIP
// purpose: Verify the no-remote-fetching WeekStrip contract.
// owns:
//   - __tests__/components/WeekStrip.test.tsx
// inputs: rendered WeekStrip with a global fetch spy and onSelect spy.
// outputs: vitest assertions.
// dependencies: @testing-library/react, vitest.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Mount, pointer enter and keyboard focus perform ZERO remote calls.
//   - Click invokes onSelect exactly once; the component issues no fetch.
//   - Public contract preserved: week-strip testid, aria labels/pressed, lock.
// failure_policy: assertion failure on any contract violation.
// END_MODULE_CONTRACT: M-TEST-WEEK-STRIP

import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { AccessInfo } from '@/lib/access'

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

describe('WeekStrip — zero remote fetching', () => {
  let fetchSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    fetchSpy = vi.fn()
    vi.stubGlobal('fetch', fetchSpy)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('performs zero remote calls on mount, hover and focus', () => {
    render(<WeekStrip selectedDate={SELECTED} access={fullAccess} />)
    const buttons = screen.getAllByRole('button')

    fireEvent.pointerEnter(buttons[0])
    fireEvent.focus(buttons[1])
    fireEvent.pointerEnter(buttons[2])
    fireEvent.focus(buttons[3])

    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('click invokes onSelect exactly once and the component never fetches', () => {
    const onSelect = vi.fn()
    render(<WeekStrip selectedDate={SELECTED} access={fullAccess} onSelect={onSelect} />)
    const buttons = screen.getAllByRole('button')

    fireEvent.click(buttons[0])

    expect(onSelect).toHaveBeenCalledTimes(1)
    expect(onSelect).toHaveBeenCalledWith(expect.any(Date))
    expect(fetchSpy).not.toHaveBeenCalled()
  })

  it('keeps the public semantic contract: root testid, aria labels/pressed, lock for inaccessible days', () => {
    render(<WeekStrip selectedDate={SELECTED} access={lockedAccess} />)
    expect(screen.getByTestId('week-strip')).toBeTruthy()

    const buttons = screen.getAllByRole('button')
    expect(buttons).toHaveLength(7)
    // The selected day is 2026-07-07 (Tuesday, monday-first index 1).
    expect(buttons[1].getAttribute('aria-pressed')).toBe('true')
    expect(buttons[0].getAttribute('aria-pressed')).toBe('false')
    // Locked days are labelled with the access requirement, and every day
    // honestly reports the unloaded status (no remote warmup).
    for (const button of buttons) {
      expect(button.getAttribute('aria-label')).toContain('статус недоступен')
    }
    expect(buttons[0].getAttribute('aria-label')).toContain('требуется доступ')
  })
})
