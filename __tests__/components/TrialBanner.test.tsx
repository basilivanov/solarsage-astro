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

  it('renders "0 дня" for daysLeft=0 (0 < 5 → дня)', () => {
    const text = getDaysLeftText(0)
    expect(text).toBe('Осталось 0 дня')
  })

  it('renders "2 дня" for daysLeft=2', () => {
    const text = getDaysLeftText(2)
    expect(text).toBe('Осталось 2 дня')
  })

  it('renders "5 дней" for daysLeft=5', () => {
    const text = getDaysLeftText(5)
    expect(text).toBe('Осталось 5 дней')
  })

  it('renders "21 дней" for daysLeft=21 (simple pluralization)', () => {
    const text = getDaysLeftText(21)
    expect(text).toBe('Осталось 21 дней')
  })
})
