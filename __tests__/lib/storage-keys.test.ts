
// ############################################################################
// AI_HEADER: MODULE_LIB_STORAGE_KEYS_TEST
// ROLE: Unit tests for storage-keys.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for storage-keys.test.ts — __tests__/lib/storage-keys.test.ts
// owns:
//   - __tests__/lib/storage-keys.test.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

import { describe, it, expect, vi } from 'vitest'
import { STORAGE_KEYS, clearAllStorage } from '../../lib/storage-keys'

describe('STORAGE_KEYS', () => {
  it('has the expected key names', () => {
    expect(STORAGE_KEYS.profile).toBe('lumen:profile')
    expect(STORAGE_KEYS.chat).toBe('lumen:chat')
    expect(STORAGE_KEYS.accessState).toBe('lumen:access-state')
    expect(STORAGE_KEYS.onboarded).toBe('lumen:onboarded')
  })

  it('all keys start with "lumen:" prefix', () => {
    for (const key of Object.values(STORAGE_KEYS)) {
      expect(key).toMatch(/^lumen:/)
    }
  })

  it('all keys are unique', () => {
    const values = Object.values(STORAGE_KEYS)
    expect(new Set(values).size).toBe(values.length)
  })
})

describe('clearAllStorage', () => {
  it('removes all STORAGE_KEYS from localStorage', () => {
    const store: Record<string, string> = {}
    for (const key of Object.values(STORAGE_KEYS)) {
      store[key] = 'some_value'
    }

    const mockLocalStorage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value },
      removeItem: (key: string) => { delete store[key] },
    }

    vi.stubGlobal('window', { localStorage: mockLocalStorage })

    clearAllStorage()

    for (const key of Object.values(STORAGE_KEYS)) {
      expect(store[key]).toBeUndefined()
    }
  })

  it('removes only storage-keys, not other keys', () => {
    const store: Record<string, string> = {
      'other:key': 'keep_me',
    }
    for (const key of Object.values(STORAGE_KEYS)) {
      store[key] = 'some_value'
    }

    const mockLocalStorage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value },
      removeItem: (key: string) => { delete store[key] },
    }

    vi.stubGlobal('window', { localStorage: mockLocalStorage })

    clearAllStorage()

    expect(store['other:key']).toBe('keep_me')
    for (const key of Object.values(STORAGE_KEYS)) {
      expect(store[key]).toBeUndefined()
    }
  })
})
