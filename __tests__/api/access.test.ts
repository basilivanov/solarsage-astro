
// ############################################################################
// AI_HEADER: MODULE_API_ACCESS_TEST
// ROLE: Unit tests for access.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for access.test.ts — __tests__/api/access.test.ts
// owns:
//   - __tests__/api/access.test.ts
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

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getAccess, getAccessAsync } from '../../lib/api/access'

describe('getAccess', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
    vi.clearAllMocks()
  })

  it('returns trial access with 14 days left', () => {
    const info = getAccess('trial')
    expect(info.hasAccess).toBe(true)
    expect(info.state).toBe('trial')
    expect(info.daysLeft).toBe(14)
    expect(info.accessStart).toBeInstanceOf(Date)
    expect(info.accessEnd).toBeInstanceOf(Date)
  })

  it('returns subscription access with 30 days left', () => {
    const info = getAccess('subscription')
    expect(info.hasAccess).toBe(true)
    expect(info.state).toBe('subscription')
    expect(info.daysLeft).toBe(30)
  })

  it('returns no access for expired state', () => {
    const info = getAccess('expired')
    expect(info.hasAccess).toBe(false)
    expect(info.state).toBe('expired')
    expect(info.daysLeft).toBe(0)
    expect(info.accessStart).toBeNull()
    expect(info.accessEnd).toBeNull()
  })

  it('returns no access for none state', () => {
    const info = getAccess('none')
    expect(info.hasAccess).toBe(false)
    expect(info.daysLeft).toBe(0)
  })

  it('getAccessAsync returns same result as getAccess', async () => {
    const sync = getAccess('trial')
    const asyncResult = await getAccessAsync('trial')
    expect(asyncResult.state).toBe(sync.state)
    expect(asyncResult.hasAccess).toBe(sync.hasAccess)
    expect(asyncResult.daysLeft).toBe(sync.daysLeft)
    expect(asyncResult.accessStart).toBeInstanceOf(Date)
    expect(asyncResult.accessEnd).toBeInstanceOf(Date)
  })

  it('computes accessEnd as start + daysLeft days', () => {
    const info = getAccess('trial')
    const expected = new Date(info.accessStart!.getTime() + 14 * 86400000)
    expect(info.accessEnd!.getTime()).toBe(expected.getTime())
  })
})
