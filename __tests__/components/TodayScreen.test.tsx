
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_TODAYSCREEN_TEST
// ROLE: Unit tests for TodayScreen.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for TodayScreentsx behavior
// owns:
//   - __tests__/components/TodayScreen.test.tsx
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import type { AccessInfo } from '@/lib/contracts/access'
import type { CalendarLunarFields } from '@/packages/contracts'
import type { AdaptedTodayPayload, TodayNote, TodayWhySection } from '@/lib/contracts/today'
import { DayChart } from '@/components/today/day-chart'
import { DayEnergyMeter } from '@/components/today/day-energy-meter'
import { DaySummaryCard } from '@/components/today/day-summary-card'

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

  const noteFixture: TodayNote = {
    id: 'note-1',
    iconName: 'compass',
    title: 'Note 1',
    description: 'Note description',
    hint: {
      meaning: 'Meaning',
      whyImportant: 'Important',
      howForMe: 'Personal context',
    },
  }

  const whyFixture: TodayWhySection = {
    id: 'why-1',
    iconName: 'telescope',
    title: 'Why',
    paragraphs: ['Why paragraph'],
  }

  function buildPayload(overrides: Partial<AdaptedTodayPayload> = {}): AdaptedTodayPayload {
    return {
      date: '2026-06-01',
      headline: '',
      dayStatus: 'steady',
      topFlags: [],
      notes: [],
      reading: { paragraphs: [] },
      why: [],
      keyInsight: 'Данные временно недоступны',
      dayChart: null,
      planetInfluences: [],
      sphereScores: [],
      ...overrides,
    }
  }

  function buildAccess(overrides: Partial<AccessInfo> = {}): AccessInfo {
    return {
      state: 'subscription',
      hasAccess: true,
      accessStart: null,
      accessEnd: null,
      daysLeft: 0,
      ...overrides,
    }
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
      notes: [noteFixture],
      reading: { paragraphs: ['p1', 'p2'] },
      why: [whyFixture],
      keyInsight: 'Why',
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

  it('renders real day chart, summary, and influence widgets from adapted payload fields', () => {
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess()}
        calendarLunar={{
          phase: 'Полнолуние',
          illumination: 97,
          moonSign: 'Sagittarius',
          lunarDay: 15,
          voidOfCourse: true,
        }}
        payload={buildPayload({
          dayStatus: 'supportive',
          dayChart: {
            source: 'solarsage',
            houses: [
              { number: 1, cuspLongitude: 0, sign: 'Aries' },
              { number: 2, cuspLongitude: 30, sign: 'Taurus' },
            ],
            transitPlanets: [
              {
                name: 'Moon',
                longitude: 42,
                sign: 'Taurus',
                retrograde: false,
                motion: 'direct',
                house: 2,
              },
              {
                name: 'Saturn',
                longitude: 132,
                sign: 'Leo',
                retrograde: true,
                motion: 'retrograde',
                house: 5,
              },
            ],
            aspects: [
              {
                planet: 'Moon',
                targetPlanet: 'Saturn',
                aspectType: 'square',
                orb: 1.4,
                strength: 0.83,
              },
            ],
          },
          planetInfluences: [
            { name: 'Moon', score: 1.25, rank: 1 },
            { name: 'Saturn', score: -0.5, rank: 2 },
          ],
          sphereScores: [{ key: 'relationships', score: 2.5, rank: 1 }],
          reading: { paragraphs: ['p1'] },
          why: [whyFixture],
          keyInsight: 'Why',
        })}
        onDateChange={onDateChange}
      />,
    )

    expect(screen.getByTestId('day-overview-card').textContent).toContain('Поддерживающий')
    expect(screen.getByTestId('day-overview-card').textContent).toContain('Полнолуние')
    expect(screen.getByTestId('day-chart').querySelectorAll('svg circle').length).toBeGreaterThan(0)
    expect(screen.getByTestId('day-energy-meter').textContent).toContain('Moon')
    expect(screen.getByTestId('day-energy-meter').textContent).toContain('relationships')
  })

  it('passes backend lunar fields through to day summary when provided', () => {
    const lunar: CalendarLunarFields = {
      phase: 'Убывающая Луна',
      illumination: 22,
      moonSign: 'Pisces',
      lunarDay: 26,
      voidOfCourse: false,
    }

    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess()}
        calendarLunar={lunar}
        payload={buildPayload({
          planetInfluences: [{ name: 'Moon', score: 1.2, rank: 1 }],
          sphereScores: [{ key: 'rest', score: 2.1, rank: 1 }],
          reading: { paragraphs: ['p1'] },
          why: [whyFixture],
          keyInsight: 'Why',
        })}
        onDateChange={onDateChange}
      />,
    )

    const summary = screen.getByTestId('day-overview-card')
    expect(summary.textContent).toContain('Убывающая Луна')
    expect(summary.textContent).toContain('22%')
    expect(summary.textContent).toContain('26 лд')
  })

  it('renders locked state with Paywall', () => {
    mockIsDayAccessible.mockReturnValue(false)
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess({ state: 'none', hasAccess: false })}
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
        access={buildAccess({ state: 'none', hasAccess: false })}
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
        access={buildAccess({ state: 'none', hasAccess: false })}
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
        access={buildAccess({ state: 'none', hasAccess: false })}
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

describe('real-data day presentation components', () => {
  it('DayChart renders non-empty SVG content from supplied real chart props', () => {
    render(
      <DayChart
        chart={{
          source: 'solarsage',
          houses: [
            { number: 1, cuspLongitude: 0, sign: 'Aries' },
            { number: 2, cuspLongitude: 30, sign: 'Taurus' },
            { number: 3, cuspLongitude: 60, sign: 'Gemini' },
          ],
          transitPlanets: [
            {
              name: 'Moon',
              longitude: 35,
              sign: 'Taurus',
              retrograde: false,
              speed: 12.5,
              motion: 'direct',
              house: 2,
            },
            {
              name: 'Sun',
              longitude: 125,
              sign: 'Leo',
              retrograde: false,
              motion: 'direct',
              house: 5,
            },
          ],
          aspects: [
            { planet: 'Moon', targetPlanet: 'Sun', aspectType: 'square', orb: 0.8, strength: 0.91 },
          ],
        }}
        dateLabel="1 июн"
        dayStatus="tense"
      />,
    )

    const chart = screen.getByTestId('day-chart')
    expect(chart.querySelector('svg')).toBeTruthy()
    expect(chart.querySelectorAll('circle').length).toBeGreaterThan(3)
    expect(chart.textContent).toContain('☽')
  })

  it('DayChart renders an unavailable state when chart data is absent', () => {
    render(<DayChart chart={null} />)
    expect(screen.getByTestId('day-chart-unavailable').textContent).toContain('Карта дня недоступна')
  })

  it('DayEnergyMeter renders supplied structured influence scores', () => {
    render(
      <DayEnergyMeter
        planetInfluences={[
          { name: 'Moon', score: 1.25, rank: 1 },
          { name: 'Mars', score: -0.4, rank: 2 },
        ]}
        sphereScores={[
          { key: 'career', score: 2.75, rank: 1 },
          { key: 'relationships', score: -1.2, rank: 2 },
        ]}
        dayStatus="steady"
      />,
    )

    expect(screen.getByTestId('day-energy-meter').textContent).toContain('Moon')
    expect(screen.getByTestId('day-energy-meter').textContent).toContain('1.25')
    expect(screen.getByTestId('day-energy-meter').textContent).toContain('career')
    expect(screen.getByTestId('day-energy-meter').textContent).toContain('2.75')
  })

  it('DaySummaryCard renders supplied backend lunar and summary facts without local calculation', () => {
    render(
      <DaySummaryCard
        date={new Date('2026-06-01T12:00:00Z')}
        dayStatus="tense"
        lunar={{
          phase: 'Полнолуние',
          illumination: 97,
          moonSign: 'Sagittarius',
          lunarDay: 15,
          voidOfCourse: true,
        }}
        planetInfluences={[{ name: 'Saturn', score: -1.75, rank: 1 }]}
        sphereScores={[{ key: 'career', score: -2, rank: 1 }]}
      />,
    )

    const summary = screen.getByTestId('day-summary-card')
    expect(summary.textContent).toContain('Полнолуние')
    expect(summary.textContent).toContain('97%')
    expect(summary.textContent).toContain('15 лунный день')
    expect(summary.textContent).toContain('Saturn')
    expect(summary.textContent).toContain('career')
    expect(summary.textContent).toContain('без курса')
  })
})
