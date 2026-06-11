
// ############################################################################
// AI_HEADER: MODULE_LIB_ICONS_TEST
// ROLE: Unit tests for icons.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for icons.test.ts — __tests__/lib/icons.test.ts
// owns:
//   - __tests__/lib/icons.test.ts
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
import { getIcon } from '../../lib/icons'

describe('getIcon', () => {
  it('returns truthy values for known icon names', () => {
    const knownIcons = [
      'moon', 'orbit', 'briefcase', 'compass', 'hourglass',
      'target', 'layers', 'trending-up', 'leaf', 'grid',
      'telescope', 'list-checks', 'zap', 'sparkle', 'check', 'building',
    ]

    for (const name of knownIcons) {
      const icon = getIcon(name)
      expect(icon).toBeTruthy()
    }
  })

  it('returns the Compass fallback for an unknown icon name', () => {
    const unknown = getIcon('nonexistent_icon')
    const compass = getIcon('compass')
    expect(unknown).toBe(compass)
  })

  it('returns fallback for empty string', () => {
    const result = getIcon('')
    const compass = getIcon('compass')
    expect(result).toBe(compass)
  })

  it('returns fallback for undefined-like input', () => {
    const result = getIcon(undefined as unknown as string)
    const compass = getIcon('compass')
    expect(result).toBe(compass)
  })

  it('known icons differ from each other where appropriate', () => {
    expect(getIcon('moon')).not.toBe(getIcon('orbit'))
    expect(getIcon('briefcase')).not.toBe(getIcon('compass'))
  })
})
