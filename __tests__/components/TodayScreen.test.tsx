
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
import { fireEvent, render, screen } from '@testing-library/react'
import React from 'react'
import type { AccessInfo } from '@/lib/contracts/access'
import type { CalendarLunarFields } from '@/packages/contracts'
import type { AdaptedTodayPayload, TodayNote, TodayWhySection } from '@/lib/contracts/today'
import { DayChart } from '@/components/today/day-chart'
import { DaySummaryCard } from '@/components/today/day-summary-card'
import { ActivationEvidenceCard } from '@/components/today/activation-evidence-card'
import { DevAuditDrawer } from '@/components/today/dev-audit-drawer'

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
    <div data-testid="why-expanded" data-open={String(Boolean(props.open))}>sections:{props.sections?.length ?? 0}</div>
  ),
}))
vi.mock('@/components/today/week-strip', () => ({
  WeekStrip: () => <div data-testid="week-strip" />,
}))
vi.mock('@/components/today/astro-history-widget', () => ({
  AstroHistoryWidget: () => <div data-testid="astro-history-widget">history</div>,
}))
vi.mock('@/components/paywall', () => ({
  Paywall: (props: any) => <div data-testid="paywall">{props.title}</div>,
}))
vi.mock('@/components/trial-banner', () => ({
  TrialBanner: (props: any) => (
    <div data-testid="trial-banner">daysLeft:{props.daysLeft}</div>
  ),
}))
vi.mock('@/components/checkin/yesterday-echo', () => ({
  YesterdayEchoLoader: () => <div data-testid="yesterday-echo-cta">check-in</div>,
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
      concreteAdvice: {
        rows: [],
        counts: { good: 0, caution: 0, avoid: 0, neutral: 0 }
      },
      daySummary: {
        statusLabel: 'Ровный день',
        statusLine: 'Сводка временно недоступна.',
        facts: []
      },
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

  it('renders accessible content in oracle section order without a standalone top headline', () => {
    const payload = buildPayload({
      headline: 'Standalone headline should not be in the top flow',
      sphereScores: [
        { key: 'thinking_speech_learning', score: 8.5, rank: 1 },
        { key: 'money_security_resources', score: 7.2, rank: 2 },
      ],
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

    const orderedIds = Array.from(screen.getByTestId('today-screen').querySelectorAll('[data-testid]'))
      .map((node) => node.getAttribute('data-testid'))
      .filter((id) =>
        [
          'day-header',
          'evening-checkin-reminder',
          'day-summary-card',
          'today-focus',
          'activation-evidence-card',
          'concrete-day-advice',
          'day-reading-disclosure',
          'day-tech-disclosure',
          'today-bottom-disclaimer',
        ].includes(id ?? ''),
      )

    // No focus and no v2 -> neither ActivationEvidenceCard nor TodayFocus is rendered
    expect(orderedIds).toEqual([
      'day-header',
      'evening-checkin-reminder',
      'day-summary-card',
      'concrete-day-advice',
      'day-reading-disclosure',
      'day-tech-disclosure',
      'today-bottom-disclaimer',
    ])
    expect(screen.queryByTestId('activation-evidence-card')).toBeNull()
    expect(screen.queryByTestId('today-focus')).toBeNull()
    expect(screen.queryByText('Standalone headline should not be in the top flow')).toBeNull()
    expect(screen.queryByTestId('today-notes')).toBeNull()
    expect(screen.getByTestId('day-reading-disclosure')).toBeTruthy()
    expect(screen.getByTestId('day-tech-disclosure')).toBeTruthy()
    expect(screen.queryByTestId('paywall')).toBeNull()
  })

  it('renders subscription and unmetered full access ready without a trial card', () => {
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess({ state: 'subscription', hasAccess: true, daysLeft: 0 })}
        payload={buildPayload()}
        onDateChange={onDateChange}
      />,
    )

    expect(screen.getByTestId('today-screen').getAttribute('data-state')).toBe('ready')
    expect(screen.queryByTestId('access-card')).toBeNull()
    expect(screen.queryByTestId('trial-banner')).toBeNull()
    expect(screen.queryByTestId('paywall')).toBeNull()
  })

  it('renders both V2 story and TodayFocusCard (F3 layers) when focus != null, focus after spheres', () => {
    const payload = buildPayload({
      focus: {
        state: 'convergence_today',
        convergence: {
          id: 'conv:1',
          themeKey: 'PLUTO',
          title: 'Что сошлось именно сегодня',
          summary: 'Сюжет дня',
          independentFactorCount: 2,
          techniqueFamilies: ['transit'],
          sourceActivationIds: ['act-1'],
        },
        events: [],
        featuredSpheres: [],
        contentState: 'ready',
      },
      v2: {
        activationSummary: { headline: 'Персональный сюжет дня', topActivatedTargets: [] },
        activationEvidence: [],
        scoreBreakdown: {},
        whyToday: [],
        audit: { available: false, payloadVersion: 'today.v2', calculationVersion: '1', scoringVersion: '1', canonVersions: {} },
      },
    })

    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess()}
        payload={payload}
        onDateChange={onDateChange}
      />,
    )

    // F3 composition (owner decision, supersedes doc 28 §3.2 either/or):
    // «ИМЕННО ДЛЯ ТЕБЯ» personal summary stays; focus is a separate layer after spheres
    expect(screen.getByTestId('today-focus')).toBeTruthy()
    expect(screen.getByTestId('activation-evidence-card')).toBeTruthy()

    const orderedIds = Array.from(screen.getByTestId('today-screen').querySelectorAll('[data-testid]'))
      .map((node) => node.getAttribute('data-testid'))
      .filter((id) =>
        ['day-summary-card', 'activation-evidence-card', 'concrete-day-advice', 'today-focus'].includes(id ?? ''),
      )
    expect(orderedIds).toEqual([
      'day-summary-card',
      'activation-evidence-card',
      'concrete-day-advice',
      'today-focus',
    ])
  })

  it('renders legacy ActivationEvidenceCard when focus == null', () => {
    const payload = buildPayload({
      focus: null,
      v2: {
        activationSummary: { headline: 'Персональный сюжет дня', topActivatedTargets: [] },
        activationEvidence: [],
        scoreBreakdown: {},
        whyToday: [],
        audit: { available: false, payloadVersion: 'today.v2', calculationVersion: '1', scoringVersion: '1', canonVersions: {} },
      },
    })

    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess()}
        payload={payload}
        onDateChange={onDateChange}
      />,
    )

    expect(screen.getByTestId('activation-evidence-card')).toBeTruthy()
    expect(screen.queryByTestId('today-focus')).toBeNull()
  })

  it('resets V2 sphere selection state when the date changes', () => {
    const payload = buildPayload({
      v2: {
        activationSummary: { headline: 'Персональный сюжет дня', topActivatedTargets: [] },
        activationEvidence: [],
        scoreBreakdown: {},
        whyToday: [],
        audit: { available: false, payloadVersion: 'today.v2', calculationVersion: '1', scoringVersion: '1', canonVersions: {} },
      },
      concreteAdvice: {
        rows: [{ key: 'work', label: 'Работа', iconName: 'briefcase', rank: 1, verdict: 'caution', confidence: 'high', text: 'Совет', evidence: [] }],
        counts: { good: 0, caution: 1, avoid: 0, neutral: 0 },
      },
    })
    const view = render(
      <TodayScreen selectedDate={selectedDate} access={buildAccess()} payload={payload} onDateChange={onDateChange} />,
    )

    fireEvent.click(screen.getByTestId('concrete-day-advice-row'))
    expect(screen.getByTestId('concrete-day-advice-row').getAttribute('data-selected')).toBe('true')

    view.rerender(
      <TodayScreen
        selectedDate={new Date('2026-06-02T12:00:00Z')}
        access={buildAccess()}
        payload={payload}
        onDateChange={onDateChange}
      />,
    )
    expect(screen.getByTestId('concrete-day-advice-row').getAttribute('data-selected')).toBe('false')
  })

  it('omits check-in on non-today routes and keeps history before disclaimer', () => {
    mockSameDay.mockReturnValue(false)
    const payload = buildPayload({
      sphereScores: [{ key: 'thinking_speech_learning', score: 8.5, rank: 1 }],
      reading: { paragraphs: ['p1'] },
      why: [whyFixture],
      keyInsight: 'Why',
    })

    render(
      <TodayScreen
        selectedDate={new Date('2026-07-05T12:00:00Z')}
        access={buildAccess()}
        payload={payload}
        onDateChange={onDateChange}
      />,
    )

    const orderedIds = Array.from(screen.getByTestId('today-screen').querySelectorAll('[data-testid]'))
      .map((node) => node.getAttribute('data-testid'))
      .filter((id) =>
        [
          'day-header',
          'evening-checkin-reminder',
          'day-summary-card',
          'concrete-day-advice',
          'today-focus',
          'day-reading-disclosure',
          'day-tech-disclosure',
          'today-bottom-disclaimer',
        ].includes(id ?? ''),
      )

    expect(screen.queryByTestId('evening-checkin-reminder')).toBeNull()
    expect(screen.queryByTestId('yesterday-echo-cta')).toBeNull()
    expect(orderedIds).toEqual([
      'day-header',
      'day-summary-card',
      'concrete-day-advice',
      'day-reading-disclosure',
      'day-tech-disclosure',
      'today-bottom-disclaimer',
    ])
  })

  it('renders real day chart, summary, and concrete advice from adapted payload fields', () => {
    render(
      <TodayScreen
        selectedDate={selectedDate}
        access={buildAccess()}
        calendarLunar={{
          phase: 'full_moon',
          phaseLabel: 'Полнолуние',
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
          concreteAdvice: {
            rows: [
              { key: 'relationships', label: 'Отношения', iconName: 'sparkle', rank: 4, verdict: 'caution', confidence: 'medium', text: 'СЕНТИНЕЛ ОТНОШЕНИЯ', evidence: [] }
            ],
            counts: { good: 0, caution: 1, avoid: 0, neutral: 0 }
          },
          daySummary: {
            statusLabel: 'Поддерживающий день',
            statusLine: 'СЕНТИНЕЛ СТАТУС ЛАЙН',
            facts: [
              { kind: 'lunar_phase', iconName: 'moon', title: 'Полнолуние', summary: '97%' }
            ]
          },
          reading: { paragraphs: ['p1'] },
          why: [whyFixture],
          keyInsight: 'Why',
        })}
        onDateChange={onDateChange}
      />,
    )

    const summaryCard = screen.getByTestId('day-summary-card')
    expect(summaryCard.textContent).toContain('Поддерживающий')
    expect(summaryCard.textContent).toContain('Полнолуние')
    expect(summaryCard.textContent).toContain('СЕНТИНЕЛ СТАТУС ЛАЙН')

    const adviceSection = screen.getByTestId('concrete-day-advice')
    expect(adviceSection).toBeTruthy()
    expect(adviceSection.textContent).toContain('Отношения')
    fireEvent.click(screen.getByTestId('concrete-day-advice-row'))
    expect(screen.getByTestId('sphere-details-sheet').textContent).toContain('СЕНТИНЕЛ ОТНОШЕНИЯ')
    expect(adviceSection.textContent).not.toContain('sparkle')
    fireEvent.click(screen.getByTestId('day-reading-disclosure-toggle'))
    expect(screen.getByTestId('day-reading')).toBeTruthy()
  })

  it('passes backend lunar fields through to day summary when provided', () => {
    const lunar: CalendarLunarFields = {
      phase: 'waning_gibbous',
      phaseLabel: 'Убывающая Луна',
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
          daySummary: {
            statusLabel: 'Ровный день',
            statusLine: 'СЕНТИНЕЛ СТАТУС ЛАЙН 2',
            facts: [
              { kind: 'lunar_phase', iconName: 'moon', title: 'Убывающая Луна', summary: '22%' }
            ]
          },
          reading: { paragraphs: ['p1'] },
          why: [whyFixture],
          keyInsight: 'Why',
        })}
        onDateChange={onDateChange}
      />,
    )

    const summary = screen.getByTestId('day-summary-card')
    expect(summary.textContent).toContain('Убывающая Луна')
    expect(summary.textContent).toContain('22%')
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
    expect(screen.getByTestId('today-screen').getAttribute('data-state')).toBe('ready')
    expect(screen.getByTestId('access-card')).toBeTruthy()
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

  it('DaySummaryCard renders supplied backend lunar and summary facts without local calculation', () => {
    render(
      <DaySummaryCard
        date={new Date('2026-06-01T12:00:00Z')}
        dayStatus="tense"
        daySummary={{
          statusLabel: 'Напряжённый день',
          statusLine: 'не решай на эмоциях — доводи начатое',
          facts: [
            { kind: 'lunar_phase', iconName: 'moon', title: 'Полнолуние', summary: '97%' },
            { kind: 'top_planet', iconName: 'Saturn', title: 'Влияние Сатурн', summary: 'тема дня — Сатурн: дисциплина и итоги' },
            { kind: 'top_flag', iconName: 'moon', title: 'Луна в Раке', summary: 'Эмоциональная глубина' }
          ]
        }}
      />,
    )

    const summary = screen.getByTestId('day-summary-card')
    expect(summary.textContent).toContain('Полнолуние')
    expect(summary.textContent).toContain('97%')
    expect(summary.textContent).toContain('Сатурн')
    expect(summary.textContent).toContain('Луна в Раке')
  })
})

describe('V2 activation evidence and audit rendering', () => {
  it('renders ActivationEvidenceCard when v2 block is present', () => {
    const v2Fixture = {
      activationSummary: {
        headline: "Сходимость на Меркурии",
        topActivatedTargets: [
          {
            targetType: "planet" as const,
            targetKey: "MERCURY",
            label: "Меркурий",
            familyCount: 2,
            techniques: ["annual_profection", "transit_to_natal"],
            spheres: ["communication"],
            activationIds: ["act-1", "act-2"],
          }
        ]
      },
      activationEvidence: [
        {
          id: "act-1",
          technique: "transit_to_natal",
          techniqueFamily: "transit",
          targetType: "planet" as const,
          targetKey: "MERCURY",
          kind: "aspect",
          active: true,
          strength: 0.8,
          evidence: "Transit Moon trine natal Mercury",
          phase: "background" as const,
          polarity: "neutral" as const,
          debug: {},
        }
      ],
      scoreBreakdown: {},
      whyToday: [],
      audit: {
        available: true,
        payloadVersion: "today.v2",
        calculationVersion: "1",
        scoringVersion: "2",
        canonVersions: {},
      }
    }

    const { getByTestId } = render(
      <ActivationEvidenceCard
        v2={v2Fixture}
        concreteAdvice={{ rows: [], counts: { good: 0, caution: 0, avoid: 0, neutral: 0 } }}
        onSphereSelect={() => {}}
       
        headlineFallback="Безопасный заголовок"
      />
    )

    const card = getByTestId('activation-evidence-card')
    expect(card).toBeTruthy()
    expect(card.textContent).toContain("Безопасный заголовок")

    expect(card.textContent).toContain("ИМЕННО ДЛЯ ТЕБЯ")
    expect(card.querySelector('[data-testid="technique-chip"]')).toBeNull()
  })

  it('renders DevAuditDrawer when forceShow is true', () => {
    const auditFixture = {
      available: true,
      payloadVersion: "today.v2",
      calculationVersion: "1.1",
      scoringVersion: "2.0",
      canonVersions: { spheres: "v1" },
    }

    const { getByTestId } = render(
      <DevAuditDrawer audit={auditFixture} forceShow={true} />
    )

    const drawer = getByTestId('dev-audit-drawer')
    expect(drawer).toBeTruthy()
    expect(drawer.textContent).toContain("Dev Audit Console")
    expect(drawer.textContent).toContain("today.v2")
  })

  it('hides DevAuditDrawer by default when forceShow is false', () => {
    const auditFixture = {
      available: true,
      payloadVersion: "today.v2",
      calculationVersion: "1.1",
      scoringVersion: "2.0",
      canonVersions: { spheres: "v1" },
    }
    const { queryByTestId } = render(
      <DevAuditDrawer audit={auditFixture} forceShow={false} />
    )
    expect(queryByTestId('dev-audit-drawer')).toBeNull()
  })
})
