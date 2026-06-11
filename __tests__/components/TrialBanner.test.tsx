
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_TRIALBANNER_TEST
// ROLE: Unit tests for TrialBanner.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for TrialBannertsx behavior
// owns:
//   - __tests__/components/TrialBanner.test.tsx
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

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
  usePathname: () => '/',
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
}))

vi.mock('lucide-react', () => ({
  Sparkles: () => <span data-testid="icon-sparkles" />,
}))

import { TrialBanner } from '@/components/trial-banner'

/** Helper: the component splits text across multiple React text nodes,
 *  so getByText('Осталось N …') fails.  We match on the sub-container's
 *  textContent instead. */
function getDaysLeftText(daysLeft: number): string | null {
  const { container } = render(<TrialBanner daysLeft={daysLeft} />)
  // The "Осталось N …" text is inside the second child div (.min-w-0 > div:nth-child(2))
  const subDivs = container.querySelectorAll('.min-w-0 > div')
  const daysDiv = subDivs[1] // second div = "Осталось N день/дня/дней"
  if (!daysDiv) return null
  const text = daysDiv.textContent ?? ''
  return text.replace(/\s+/g, ' ').trim()
}

describe('TrialBanner', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.NEXT_PUBLIC_DEV_MODE = 'false'
  })

  it('renders days left with correct pluralization for 1', () => {
    render(<TrialBanner daysLeft={1} />)
    expect(screen.getByText('Осталось 1 день')).toBeTruthy()
  })

  it('renders days left with correct pluralization for 3', () => {
    render(<TrialBanner daysLeft={3} />)
    expect(screen.getByText('Осталось 3 дня')).toBeTruthy()
  })

  it('renders days left with correct pluralization for 10', () => {
    render(<TrialBanner daysLeft={10} />)
    expect(screen.getByText('Осталось 10 дней')).toBeTruthy()
  })

  it('renders "0 дней" for daysLeft=0', () => {
    const text = getDaysLeftText(0)
    expect(text).toBe('Осталось 0 дней')
  })

  it('renders "2 дня" for daysLeft=2', () => {
    const text = getDaysLeftText(2)
    expect(text).toBe('Осталось 2 дня')
  })

  it('renders "5 дней" for daysLeft=5', () => {
    const text = getDaysLeftText(5)
    expect(text).toBe('Осталось 5 дней')
  })

  it('renders "21 день" for daysLeft=21 (correct Russian plural)', () => {
    const text = getDaysLeftText(21)
    expect(text).toBe('Осталось 21 день')
  })

  it('renders "22 дня" for daysLeft=22', () => {
    const text = getDaysLeftText(22)
    expect(text).toBe('Осталось 22 дня')
  })

  it('renders "11 дней" for daysLeft=11 (teen exception)', () => {
    const text = getDaysLeftText(11)
    expect(text).toBe('Осталось 11 дней')
  })

  it('renders "101 день" for daysLeft=101', () => {
    const text = getDaysLeftText(101)
    expect(text).toBe('Осталось 101 день')
  })
})
