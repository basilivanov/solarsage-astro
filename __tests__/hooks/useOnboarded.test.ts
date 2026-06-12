
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USEONBOARDED_TEST
// ROLE: Unit tests for useOnboarded.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for useOnboardedts behavior
// owns:
//   - __tests__/hooks/useOnboarded.test.ts
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
import { renderHook, act, waitFor } from '@testing-library/react'

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

const store = new Map<string, string>()

beforeEach(() => {
  store.clear()
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
  })
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: vi.fn((key: string) => store.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => store.set(key, value)),
      removeItem: vi.fn((key: string) => store.delete(key)),
    },
    writable: true,
  })
})

import { useOnboarded } from '@/hooks/use-onboarded'

describe('useOnboarded', () => {
  it('returns onboarded=false when no localStorage entry', async () => {
    const { result } = renderHook(() => useOnboarded())
    await waitFor(() => expect(result.current.onboarded).toBe(false))
  })

  it('reads onboarded=true from localStorage on mount', async () => {
    store.set('lumen:onboarded', '1')
    const { result } = renderHook(() => useOnboarded())
    await waitFor(() => expect(result.current.onboarded).toBe(true))
  })

  it('reads any non-"1" value as false', async () => {
    store.set('lumen:onboarded', '0')
    const { result } = renderHook(() => useOnboarded())
    await waitFor(() => expect(result.current.onboarded).toBe(false))
  })

  it('setOnboarded(true) writes "1" to localStorage', async () => {
    const { result } = renderHook(() => useOnboarded())
    act(() => result.current.setOnboarded(true))
    await waitFor(() => expect(result.current.onboarded).toBe(true))
    expect(store.get('lumen:onboarded')).toBe('1')
  })

  it('setOnboarded(false) removes key from localStorage', async () => {
    store.set('lumen:onboarded', '1')
    const { result } = renderHook(() => useOnboarded())
    await waitFor(() => expect(result.current.onboarded).toBe(true))

    act(() => result.current.setOnboarded(false))
    expect(result.current.onboarded).toBe(false)
    expect(store.has('lumen:onboarded')).toBe(false)
  })

  it('resetOnboarded removes key and sets false', async () => {
    store.set('lumen:onboarded', '1')
    const { result } = renderHook(() => useOnboarded())
    await waitFor(() => expect(result.current.onboarded).toBe(true))

    act(() => result.current.resetOnboarded())
    expect(result.current.onboarded).toBe(false)
    expect(store.has('lumen:onboarded')).toBe(false)
  })
})
