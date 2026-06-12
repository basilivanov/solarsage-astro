
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_ERRORBOUNDARY_TEST
// ROLE: Unit tests for ErrorBoundary.test.tsx
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for ErrorBoundarytsx behavior
// owns:
//   - __tests__/components/ErrorBoundary.test.tsx
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

  it('renders "Debug Info" button when in dev mode', () => {
    process.env.NEXT_PUBLIC_DEV_MODE = 'true'
    render(<ErrorBoundary error={error} />)
    expect(screen.getByText('Debug Info')).toBeTruthy()
  })

  it('falls back to "Произошла неизвестная ошибка" when error has no message', () => {
    const errorNoMessage = new Error()
    errorNoMessage.message = ''
    render(<ErrorBoundary error={errorNoMessage} />)
    expect(screen.getByTestId('error-message').textContent).toBe(
      'Произошла неизвестная ошибка',
    )
  })

  it('custom message prop overrides error.message', () => {
    render(<ErrorBoundary error={error} message="Кастомное сообщение" />)
    expect(screen.getByTestId('error-message').textContent).toBe('Кастомное сообщение')
  })

  it('has role="alert" for accessibility', () => {
    render(<ErrorBoundary error={error} />)
    expect(screen.getByRole('alert')).toBeTruthy()
  })

  it('has data-testid="error-boundary"', () => {
    render(<ErrorBoundary error={error} />)
    expect(screen.getByTestId('error-boundary')).toBeTruthy()
  })
})
