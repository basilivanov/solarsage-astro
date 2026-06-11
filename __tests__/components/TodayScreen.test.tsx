
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_TODAYSCREEN_TEST
// ROLE: Unit tests for TodayScreen.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for TodayScreen.test.tsx — __tests__/components/TodayScreen.test.tsx
// owns:
//   - __tests__/components/TodayScreen.test.tsx
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
import { render, screen } from '@testing-library/react'
import React from 'react'

// Polyfill PointerEvent for jsdom (Node 20/jsdom lacks it)
if (typeof PointerEvent === 'undefined') {
  ;(globalThis as any).PointerEvent = class PointerEvent extends MouseEvent {
    declare pointerId: number
    constructor(type: string, init?: any) {
      super(type, init)
      this.pointerId = init?.pointerId ?? 0
    }
  }
}

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
  usePathname: () => '/',
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock('@/components/today/date-header', () => ({
  DateHeader: (props: any) => (
    <div data-testid="date-header">
      locked:{String(props.locked)} canPrev:{String(props.canPrev)} canNext:{String(props.canNext)}
    </div>
  ),
}))
vi.mock('@/components/today/today-notes', () => ({
  TodayNotes: (props: any) => (
    <div data-testid="today-notes">
      heading:{props.heading || 'default'} limit:{props.limit ?? 'none'}
    </div>
  ),
}))
vi.mock('@/components/today/day-reading', () => ({
  DayReading: (props: any) => (
    <div data-testid="day-reading">preview:{String(!!props.preview)}</div>
  ),
}))
vi.mock('@/components/today/why-expanded', () => ({
  WhyExpanded: (props: any) => (
    <div data-testid="why-expanded">sections:{props.sections?.length ?? 0}</div>
  ),
}))
vi.mock('@/components/today/week-strip', () => ({
  WeekStrip: () => <div data-testid="week-strip" />,
}))
vi.mock('@/components/paywall', () => ({
  Paywall: (props: any) => <div data-testid="paywall">{props.title}</div>,
}))
vi.mock('@/components/trial-banner', () => ({
  TrialBanner: (props: any) => (
    <div data-testid="trial-banner">daysLeft:{props.daysLeft}</div>
  ),
}))

const { mockAddDays, mockSameDay, mockIsDayAccessible } = vi.hoisted(() => ({
  mockAddDays: vi.fn(),
  mockSameDay: vi.fn(),
  mockIsDayAccessible: vi.fn(),
}))

vi.mock('@/lib/today', () => ({
  addDays: mockAddDays,
  sameDay: mockSameDay,
  TODAY: new Date('2026-06-01T12:00:00Z'),
}))

vi.mock('@/lib/access', () => ({
  isDayAccessible: mockIsDayAccessible,
}))

import { TodayScreen } from '@/components/today/today-screen'

describe('TodayScreen', () => {
  const selectedDate = new Date('2026-06-01T12:00:00Z')
  const onDateChange = vi.fn()

  function buildPayload(overrides: Record<string, any> = {}) {
    return {
      notes: [],
      reading: { paragraphs: [] },
      why: [],
      keyInsight: null,
      ...overrides,
    } as any
  }

  function buildAccess(overrides: Record<string, any> = {}) {
    return { state: 'active', daysLeft: 0, ...overrides } as any
  }

  beforeEach(() => {
    vi.clearAllMocks()
    mockSameDay.mockReturnValue(true)
    mockIsDayAccessible.mockReturnValue(true)
    mockAddDays.mockImplementation((d: Date, n: number) => {
      const next = new Date(d)
      next.setDate(next.getDate() + n)
      return next
    })
  })

  it('renders accessible content: notes, reading, why, week-strip', () => {
    const payload = buildPayload({
      notes: [{ text: 'Note 1' }],
      reading: { paragraphs: ['p1', 'p2'] },
      why: [{ title: 'Why' }],
    })
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess()}
        payload={payload}
        onDateChange={onDateChange}
      />,
    )
    expect(screen.getByTestId('today-notes')).toBeTruthy()
    expect(screen.getByTestId('day-reading')).toBeTruthy()
    expect(screen.getByTestId('why-expanded')).toBeTruthy()
    expect(screen.getByTestId('week-strip')).toBeTruthy()
    expect(screen.queryByTestId('paywall')).toBeNull()
  })

  it('renders locked state with Paywall', () => {
    mockIsDayAccessible.mockReturnValue(false)
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess({ state: 'locked' })}
        payload={buildPayload()}
        onDateChange={onDateChange}
      />,
    )
    expect(screen.getByTestId('paywall')).toBeTruthy()
  })

  it('renders notes with limit in locked/preview state', () => {
    mockIsDayAccessible.mockReturnValue(false)
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess({ state: 'locked' })}
        payload={buildPayload()}
        onDateChange={onDateChange}
      />,
    )
    const notes = screen.getByTestId('today-notes')
    expect(notes.textContent).toContain('limit:2')
    expect(notes.textContent).toContain('heading:Главное на этот день')
  })

  it('renders day-reading in preview mode when locked', () => {
    mockIsDayAccessible.mockReturnValue(false)
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess({ state: 'locked' })}
        payload={buildPayload()}
        onDateChange={onDateChange}
      />,
    )
    expect(screen.getByTestId('day-reading').textContent).toContain('preview:true')
  })

  it('renders TrialBanner when access state is trial', () => {
    mockIsDayAccessible.mockReturnValue(true)
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess({ state: 'trial', daysLeft: 5 })}
        payload={buildPayload()}
        onDateChange={onDateChange}
      />,
    )
    const banner = screen.getByTestId('trial-banner')
    expect(banner.textContent).toContain('daysLeft:5')
  })

  it('shows today-specific paywall title when locked on today', () => {
    mockIsDayAccessible.mockReturnValue(false)
    mockSameDay.mockReturnValue(true)
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess({ state: 'locked' })}
        payload={buildPayload()}
        onDateChange={onDateChange}
      />,
    )
    expect(screen.getByTestId('paywall').textContent).toContain(
      'Твой персональный разбор на сегодня уже готов',
    )
  })

  it('swipe right (pointer) triggers onDateChange with previous day', () => {
    mockIsDayAccessible.mockReturnValue(true)
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess()}
        payload={buildPayload()}
        onDateChange={onDateChange}
      />,
    )
    const el = screen.getByTestId('today-screen')
    el.dispatchEvent(new PointerEvent('pointerdown', { clientX: 200, clientY: 100, pointerId: 1, bubbles: true }))
    el.dispatchEvent(new PointerEvent('pointerup', { clientX: 300, clientY: 110, pointerId: 1, bubbles: true }))
    expect(onDateChange).toHaveBeenCalledTimes(1)
  })

  it('swipe left (pointer) triggers onDateChange with next day', () => {
    mockIsDayAccessible.mockReturnValue(true)
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess()}
        payload={buildPayload()}
        onDateChange={onDateChange}
      />,
    )
    const el = screen.getByTestId('today-screen')
    el.dispatchEvent(new PointerEvent('pointerdown', { clientX: 300, clientY: 100, pointerId: 1, bubbles: true }))
    el.dispatchEvent(new PointerEvent('pointerup', { clientX: 200, clientY: 110, pointerId: 1, bubbles: true }))
    expect(onDateChange).toHaveBeenCalledTimes(1)
  })
})
