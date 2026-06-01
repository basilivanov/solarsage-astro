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
  Sun: () => <span data-testid="icon-sun" />,
  CalendarDays: () => <span data-testid="icon-calendar" />,
  BookOpen: () => <span data-testid="icon-book" />,
  User: () => <span data-testid="icon-user" />,
  MessageCircle: () => <span data-testid="icon-message" />,
}))

vi.mock('@/lib/today', () => ({
  TODAY: new Date('2026-06-01T12:00:00Z'),
}))

vi.mock('@/lib/date', () => ({
  toDateParam: () => '2026-06-01',
}))

import { TabBar } from '@/components/today/tab-bar'

describe('TabBar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders all 5 tabs', () => {
    render(<TabBar />)
    expect(screen.getByText('Сегодня')).toBeTruthy()
    expect(screen.getByText('Календарь')).toBeTruthy()
    expect(screen.getByText('Разборы')).toBeTruthy()
    expect(screen.getByText('Спросить')).toBeTruthy()
    expect(screen.getByText('Профиль')).toBeTruthy()
  })

  it('highlights "Сегодня" tab as active when pathname is /', () => {
    render(<TabBar />)
    const todayLink = screen.getByText('Сегодня').closest('a')
    expect(todayLink?.getAttribute('aria-current')).toBe('page')
    const calendarLink = screen.getByText('Календарь').closest('a')
    expect(calendarLink?.getAttribute('aria-current')).toBeNull()
  })

  it('has correct hrefs for all tabs', () => {
    render(<TabBar />)
    const links = screen.getAllByRole('link')
    const hrefs = links.map((l) => l.getAttribute('href'))
    expect(hrefs).toContain('/calendar')
    expect(hrefs).toContain('/readings')
    expect(hrefs).toContain('/chat')
    expect(hrefs).toContain('/profile')
  })

  it('renders correct tab labels', () => {
    render(<TabBar />)
    const labels = ['Сегодня', 'Календарь', 'Разборы', 'Спросить', 'Профиль']
    for (const label of labels) {
      expect(screen.getByText(label)).toBeTruthy()
    }
  })
})
