
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USEPROFILE_TEST
// ROLE: Unit tests for useProfile.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for useProfilets behavior
// owns:
//   - __tests__/hooks/useProfile.test.ts
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

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

const profileStore = new Map<string, string>()

beforeEach(() => {
  profileStore.clear()
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: vi.fn((key: string) => profileStore.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => profileStore.set(key, value)),
      removeItem: vi.fn((key: string) => profileStore.delete(key)),
    },
    writable: true,
  })
})

import { DEFAULT_PROFILE, type Profile } from '@/lib/profile'
import { useProfile as useProfileHook } from '@/hooks/use-profile'

describe('useProfile', () => {
  it('loads default profile when localStorage is empty', () => {
    const { result } = renderHook(() => useProfileHook())
    expect(result.current.loaded).toBe(true)
    expect(result.current.profile).toEqual(DEFAULT_PROFILE)
  })

  it('loads saved profile from localStorage', () => {
    const saved: Profile = {
      ...DEFAULT_PROFILE,
      birthPlace: 'Москва, Россия',
    }
    profileStore.set('lumen:profile', JSON.stringify(saved))

    const { result } = renderHook(() => useProfileHook())
    expect(result.current.profile.birthPlace).toBe('Москва, Россия')
  })

  it('update applies partial patch and persists', () => {
    const { result } = renderHook(() => useProfileHook())
    act(() => result.current.update({ birthPlace: 'Одесса, Украина' }))
    expect(result.current.profile.birthPlace).toBe('Одесса, Украина')

    const stored = JSON.parse(profileStore.get('lumen:profile')!)
    expect(stored.birthPlace).toBe('Одесса, Украина')
  })

  it('update merges multiple fields', () => {
    const { result } = renderHook(() => useProfileHook())
    act(() =>
      result.current.update({
        birthPlace: 'Париж, Франция',
        currentCity: 'Лондон, Великобритания',
      })
    )
    expect(result.current.profile.birthPlace).toBe('Париж, Франция')
    expect(result.current.profile.currentCity).toBe('Лондон, Великобритания')
    // default fields remain
    expect(result.current.profile.birthDate.day).toBe('14')
  })

  it('ignores invalid localStorage JSON, falls back to default', () => {
    profileStore.set('lumen:profile', '{broken')
    const { result } = renderHook(() => useProfileHook())
    expect(result.current.profile).toEqual(DEFAULT_PROFILE)
  })
})
