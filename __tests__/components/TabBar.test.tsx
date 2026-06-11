import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

const { mockPathname } = vi.hoisted(() => ({
  mockPathname: vi.fn(() => '/'),
}))

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: vi.fn(), push: vi.fn(), back: vi.fn() }),
  usePathname: () => mockPathname(),
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
    mockPathname.mockReturnValue('/')
  })

  it('renders nav with data-testid today-tab-bar', () => {
    render(<TabBar />)
    expect(screen.getByTestId('today-tab-bar')).toBeTruthy()
  })

  it('renders all 5 tabs with data-testid attributes', () => {
    render(<TabBar />)
    const keys = ['today', 'calendar', 'readings', 'chat', 'profile']
    for (const key of keys) {
      expect(screen.getByTestId(`today-tab-${key}`)).toBeTruthy()
    }
  })

  it('renders all five link labels', () => {
    render(<TabBar />)
    const labels = ['Сегодня', 'Календарь', 'Разборы', 'Спросить', 'Профиль']
    for (const label of labels) {
      expect(screen.getByText(label)).toBeTruthy()
    }
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

  it('highlights "Сегодня" tab as active when pathname is /', () => {
    render(<TabBar />)
    const todayLink = screen.getByTestId('today-tab-today')
    expect(todayLink.getAttribute('aria-current')).toBe('page')
    const calendarLink = screen.getByTestId('today-tab-calendar')
    expect(calendarLink.getAttribute('aria-current')).toBeNull()
  })

  it('highlights "Календарь" tab as active when pathname is /calendar', () => {
    mockPathname.mockReturnValue('/calendar')
    render(<TabBar />)
    const calendarLink = screen.getByTestId('today-tab-calendar')
    expect(calendarLink.getAttribute('aria-current')).toBe('page')
    const todayLink = screen.getByTestId('today-tab-today')
    expect(todayLink.getAttribute('aria-current')).toBeNull()
  })

  it('highlights "Спросить" tab as active when pathname is /chat', () => {
    mockPathname.mockReturnValue('/chat')
    render(<TabBar />)
    const chatLink = screen.getByTestId('today-tab-chat')
    expect(chatLink.getAttribute('aria-current')).toBe('page')
  })

  it('falls back to "/" when usePathname returns null', () => {
    mockPathname.mockReturnValue(null as any)
    render(<TabBar />)
    const todayLink = screen.getByTestId('today-tab-today')
    expect(todayLink.getAttribute('aria-current')).toBe('page')
  })

  it('sets aria-current="page" on the active tab only', () => {
    render(<TabBar />)
    const todayLink = screen.getByTestId('today-tab-today')
    expect(todayLink.getAttribute('aria-current')).toBe('page')
    const calendarLink = screen.getByTestId('today-tab-calendar')
    expect(calendarLink.getAttribute('aria-current')).toBeNull()
    const chatLink = screen.getByTestId('today-tab-chat')
    expect(chatLink.getAttribute('aria-current')).toBeNull()
  })
})
