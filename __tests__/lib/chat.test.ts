
// ############################################################################
// AI_HEADER: MODULE_LIB_CHAT_TEST
// ROLE: Unit tests for chat.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for chat.test.ts — __tests__/lib/chat.test.ts
// owns:
//   - __tests__/lib/chat.test.ts
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

import { describe, it, expect } from 'vitest'
import { buildContextSummary, suggestedPrompts } from '../../lib/chat'
import { DEFAULT_PROFILE } from '../../lib/profile'

describe('buildContextSummary', () => {
  it('returns a summary string containing birth date and place', () => {
    const summary = buildContextSummary(DEFAULT_PROFILE)
    expect(summary).toContain('14 июля 1995')
    expect(summary).toContain('08:42')
    expect(summary).toContain('Киев, Украина')
  })

  it('returns "Не указано" for invalid birth date in summary', () => {
    const profile = {
      ...DEFAULT_PROFILE,
      birthDate: { day: '99', month: '99', year: 'abcd' },
    }
    const summary = buildContextSummary(profile)
    expect(summary).toContain('Не указано')
  })

  it('returns "Не знаю" when time is unknown', () => {
    const profile = {
      ...DEFAULT_PROFILE,
      birthTime: { hours: '00', minutes: '00', unknown: true },
    }
    const summary = buildContextSummary(profile)
    expect(summary).toContain('Не знаю')
  })
})

describe('suggestedPrompts', () => {
  it('returns an array of 4 prompt strings', () => {
    const prompts = suggestedPrompts(DEFAULT_PROFILE)
    expect(prompts).toHaveLength(4)
    for (const p of prompts) {
      expect(typeof p).toBe('string')
      expect(p.length).toBeGreaterThan(0)
    }
  })

  it('returns the same prompts regardless of profile', () => {
    const modified = { ...DEFAULT_PROFILE, birthPlace: 'Другое место' }
    expect(suggestedPrompts(modified)).toEqual(suggestedPrompts(DEFAULT_PROFILE))
  })
})
