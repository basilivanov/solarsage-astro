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
})
