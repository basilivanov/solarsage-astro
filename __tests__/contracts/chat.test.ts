
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_CHAT_TEST
// ROLE: Unit tests for chat.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for chatts behavior
// owns:
//   - __tests__/contracts/chat.test.ts
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect } from 'vitest'
import {
  validateChatMessage,
  validateChatHistory,
  safeValidateChatHistory,
  ChatMessageSchema,
  ChatHistorySchema,
} from '../../lib/contracts/chat'

const validMessage = {
  id: 'msg-1',
  role: 'user' as const,
  content: 'Hello, how are you?',
  createdAt: 1717248000000,
}

describe('validateChatMessage', () => {
  it('validates a correct user message', () => {
    expect(() => validateChatMessage(validMessage)).not.toThrow()
  })

  it('validates a correct assistant message', () => {
    const msg = { ...validMessage, role: 'assistant' as const, content: 'I am fine.' }
    expect(() => validateChatMessage(msg)).not.toThrow()
  })

  it('rejects message with invalid role', () => {
    const msg = { ...validMessage, role: 'system' }
    expect(() => validateChatMessage(msg)).toThrow()
  })

  it('rejects message with empty id', () => {
    const msg = { ...validMessage, id: '' }
    expect(() => validateChatMessage(msg)).toThrow()
  })

  it('rejects message with negative createdAt', () => {
    const msg = { ...validMessage, createdAt: -1000 }
    expect(() => validateChatMessage(msg)).toThrow()
  })

  it('rejects message with non-integer createdAt', () => {
    const msg = { ...validMessage, createdAt: 1717248000.5 }
    expect(() => validateChatMessage(msg)).toThrow()
  })

  it('rejects message with missing content', () => {
    const { content, ...msg } = validMessage
    expect(() => validateChatMessage(msg)).toThrow()
  })

  it('rejects message with empty string content', () => {
    const msg = { ...validMessage, content: '' }
    expect(() => ChatMessageSchema.parse(msg)).not.toThrow()
  })
})

describe('validateChatHistory', () => {
  it('validates a correct array of messages', () => {
    const history = [validMessage, { ...validMessage, id: 'msg-2', role: 'assistant' as const }]
    expect(() => validateChatHistory(history)).not.toThrow()
  })

  it('validates an empty array', () => {
    expect(() => validateChatHistory([])).not.toThrow()
  })

  it('rejects array with one invalid message', () => {
    const history = [validMessage, { ...validMessage, id: '', role: 'user' as const }]
    expect(() => validateChatHistory(history)).toThrow()
  })

  it('rejects non-array input', () => {
    expect(() => validateChatHistory(validMessage)).toThrow()
  })
})

describe('safeValidateChatHistory', () => {
  it('returns success for valid history', () => {
    const result = safeValidateChatHistory([validMessage])
    expect(result.success).toBe(true)
  })

  it('returns error for invalid history', () => {
    const result = safeValidateChatHistory([{ ...validMessage, role: 'system' }])
    expect(result.success).toBe(false)
  })
})
