import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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
  Lock: () => <span data-testid="icon-lock" />,
  Crown: () => <span data-testid="icon-crown" />,
  UserPlus: () => <span data-testid="icon-user-plus" />,
}))

vi.mock('@/lib/utils', () => ({
  cn: (...args: any[]) => args.filter(Boolean).join(' '),
}))

const mockFetch = vi.fn()

import { Paywall } from '@/components/paywall'

describe('Paywall', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    globalThis.fetch = mockFetch
    mockFetch.mockResolvedValue({
      json: () => Promise.resolve({ inviteUrl: 'https://t.me/invite-link' }),
    })
  })

  it('renders default title', () => {
    render(<Paywall />)
    expect(
      screen.getByText('Твой персональный разбор уже готов'),
    ).toBeTruthy()
  })

  it('renders custom title', () => {
    render(<Paywall title="Custom paywall title" />)
    expect(screen.getByText('Custom paywall title')).toBeTruthy()
  })

  it('renders subscribe button', () => {
    render(<Paywall />)
    expect(screen.getByText('Оформить подписку')).toBeTruthy()
  })

  it('renders invite button', () => {
    render(<Paywall />)
    expect(screen.getByText('Пригласить друга · +14 дней')).toBeTruthy()
  })

  it('calls fetch for referral URL on mount', async () => {
    render(<Paywall />)
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith(
        '/api/referral',
        { credentials: 'include' },
      )
    })
  })
})
