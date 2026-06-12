
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USEACCESS_TEST
// ROLE: Unit tests for useAccess.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for useAccessts behavior
// owns:
//   - __tests__/hooks/useAccess.test.ts
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
import { renderHook, act } from '@testing-library/react'

const storage = new Map<string, string>()

beforeEach(() => {
  storage.clear()
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: vi.fn((key: string) => storage.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => storage.set(key, value)),
      removeItem: vi.fn((key: string) => storage.delete(key)),
    },
    writable: true,
  })
})

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

import { useAccess } from '@/hooks/use-access'

describe('useAccess', () => {
  it('returns trial state by default when no localStorage entry', () => {
    const { result } = renderHook(() => useAccess())
    expect(result.current.state).toBe('trial')
    expect(result.current.access.hasAccess).toBe(true)
    expect(result.current.access.daysLeft).toBe(14)
  })

  it('reads saved state from localStorage on mount', () => {
    storage.set('lumen:access-state', 'subscription')
    const { result } = renderHook(() => useAccess())
    expect(result.current.state).toBe('subscription')
    expect(result.current.access.daysLeft).toBe(30)
  })

  it('falls back to trial for unknown localStorage value', () => {
    storage.set('lumen:access-state', 'banana')
    const { result } = renderHook(() => useAccess())
    expect(result.current.state).toBe('trial')
  })

  it('setState updates state and persists to localStorage', () => {
    const { result } = renderHook(() => useAccess())
    act(() => result.current.setState('expired'))
    expect(result.current.state).toBe('expired')
    expect(storage.get('lumen:access-state')).toBe('expired')
  })

  it('returns correct access info for each state', () => {
    const { result, rerender } = renderHook(() => useAccess())

    act(() => result.current.setState('none'))
    expect(result.current.state).toBe('none')
    expect(result.current.access.hasAccess).toBe(false)
    expect(result.current.access.daysLeft).toBe(0)

    act(() => result.current.setState('expired'))
    expect(result.current.state).toBe('expired')
    expect(result.current.access.hasAccess).toBe(false)
    expect(result.current.access.daysLeft).toBe(0)

    act(() => result.current.setState('subscription'))
    expect(result.current.state).toBe('subscription')
    expect(result.current.access.hasAccess).toBe(true)
    expect(result.current.access.daysLeft).toBe(30)
  })

  it('access info has start/end dates when active', () => {
    const { result } = renderHook(() => useAccess())
    expect(result.current.access.accessStart).toBeInstanceOf(Date)
    expect(result.current.access.accessEnd).toBeInstanceOf(Date)
  })
})
