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
})
