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

import { ErrorBoundary } from '@/components/grace/ErrorBoundary'

describe('ErrorBoundary', () => {
  const error = new Error('Something went wrong')

  beforeEach(() => {
    vi.clearAllMocks()
    process.env.NEXT_PUBLIC_DEV_MODE = 'false'
  })

  it('renders error message', () => {
    render(<ErrorBoundary error={error} />)
    expect(screen.getByTestId('error-message').textContent).toBe(
      'Something went wrong',
    )
  })

  it('renders custom title', () => {
    render(<ErrorBoundary error={error} title="Custom Error Title" />)
    expect(screen.getByText('Custom Error Title')).toBeTruthy()
  })

  it('does not render debug button when not in dev mode', () => {
    render(<ErrorBoundary error={error} />)
    expect(screen.queryByText('Debug Info')).toBeNull()
  })
})
