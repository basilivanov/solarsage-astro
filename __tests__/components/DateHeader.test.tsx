
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_DATEHEADER_TEST
// ROLE: Unit tests for DateHeader.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for DateHeader.test.tsx — __tests__/components/DateHeader.test.tsx
// owns:
//   - __tests__/components/DateHeader.test.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import React from 'react'

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

vi.mock('lucide-react', () => ({
  ChevronLeft: () => <span data-testid="icon-chevron-left" />,
  ChevronRight: () => <span data-testid="icon-chevron-right" />,
  Lock: () => <span data-testid="icon-lock" />,
}))

const { mockSameDay } = vi.hoisted(() => ({
  mockSameDay: vi.fn(),
}))

vi.mock('@/lib/today', () => ({
  sameDay: mockSameDay,
  TODAY: new Date('2026-06-01T12:00:00Z'),
}))

vi.mock('@/lib/date', () => ({
  formatDayMonth: vi.fn((d: Date) => `${d.getDate()} июня`),
}))

import { DateHeader } from '@/components/today/date-header'

describe('DateHeader', () => {
  const date = new Date('2026-06-01T12:00:00Z')

  beforeEach(() => {
    vi.clearAllMocks()
    mockSameDay.mockReturnValue(true)
  })

  it('renders formatted date', () => {
    render(<DateHeader date={date} />)
    expect(screen.getByTestId('today-headline').textContent).toBe('1 июня')
  })

  it('shows "Сегодня" label for today', () => {
    render(<DateHeader date={date} />)
    expect(screen.getByText('Сегодня')).toBeTruthy()
  })

  it('shows "День" label when not today', () => {
    mockSameDay.mockReturnValue(false)
    render(<DateHeader date={date} />)
    expect(screen.getByText('День')).toBeTruthy()
  })

  it('shows lock icon when locked', () => {
    render(<DateHeader date={date} locked />)
    expect(screen.getByTestId('icon-lock')).toBeTruthy()
  })

  it('calls onPrev and onNext on arrow button clicks', () => {
    const onPrev = vi.fn()
    const onNext = vi.fn()
    render(
      <DateHeader date={date} onPrev={onPrev} onNext={onNext} />,
    )
    fireEvent.click(screen.getByLabelText('Предыдущий день'))
    expect(onPrev).toHaveBeenCalledTimes(1)
    fireEvent.click(screen.getByLabelText('Следующий день'))
    expect(onNext).toHaveBeenCalledTimes(1)
  })

  it('disables previous button when canPrev is false', () => {
    render(<DateHeader date={date} canPrev={false} />)
    const prevBtn = screen.getByLabelText('Предыдущий день')
    expect(prevBtn.hasAttribute('disabled')).toBe(true)
  })

  it('disables next button when canNext is false', () => {
    render(<DateHeader date={date} canNext={false} />)
    const nextBtn = screen.getByLabelText('Следующий день')
    expect(nextBtn.hasAttribute('disabled')).toBe(true)
  })

  it('disables both buttons when canPrev and canNext are false simultaneously', () => {
    render(<DateHeader date={date} canPrev={false} canNext={false} />)
    expect(screen.getByLabelText('Предыдущий день').hasAttribute('disabled')).toBe(true)
    expect(screen.getByLabelText('Следующий день').hasAttribute('disabled')).toBe(true)
  })

  it('has data-testid="today-headline" on the date span', () => {
    render(<DateHeader date={date} />)
    expect(screen.getByTestId('today-headline')).toBeTruthy()
  })
})
