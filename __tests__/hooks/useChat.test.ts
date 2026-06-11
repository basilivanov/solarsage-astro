
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USECHAT_TEST
// ROLE: Unit tests for useChat.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for useChatts behavior
// owns:
//   - __tests__/hooks/useChat.test.ts
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
import { renderHook, waitFor, act } from '@testing-library/react'
import type { ChatMessage } from '@/lib/chat'

vi.mock('@/lib/log', () => ({
  logger: { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() },
}))

// ── localStorage mock store (shared across mock setup) ──
const chatStorage = new Map<string, string>()

// ── Hoisted mock setup ──
const { mockSendMessage, mockChatReducer, mockInitialChatState } = vi.hoisted(() => {
  // reducer that matches useChat's dispatch events
  const ms = new Map<string, string>()

  const mockInitial = {
    messages: [] as ChatMessage[],
    pending: false,
    streamingId: null as string | null,
    hydrated: false,
  }

  function reducer(state: typeof mockInitial, event: any): typeof mockInitial {
    switch (event.type) {
      case 'hydrated':
        return { ...state, messages: event.messages, hydrated: true }
      case 'user_sent':
        return {
          ...state,
          pending: true,
          messages: [
            ...state.messages,
            { id: event.id, role: 'user' as const, content: event.text, createdAt: event.createdAt },
          ],
        }
      case 'stream_started':
        return { ...state, streamingId: event.id }
      case 'token': {
        const idx = state.messages.findIndex(
          (m: ChatMessage) => m.id === event.id && m.role === 'assistant',
        )
        if (idx >= 0) {
          const updated = [...state.messages]
          updated[idx] = { ...updated[idx], content: event.content }
          return { ...state, messages: updated }
        }
        return {
          ...state,
          messages: [
            ...state.messages,
            { id: event.id, role: 'assistant' as const, content: event.content, createdAt: Date.now() },
          ],
        }
      }
      case 'done':
        return { ...state, pending: false, streamingId: null }
      case 'aborted':
        return { ...state, pending: false, streamingId: null }
      case 'error':
        return { ...state, pending: false, streamingId: null, messages: [...state.messages, event.message] }
      case 'reset':
        return { ...mockInitial, hydrated: true }
      default:
        return state
    }
  }

  return {
    mockSendMessage: vi.fn(),
    mockChatReducer: reducer,
    mockInitialChatState: mockInitial,
  }
})

vi.mock('@/lib/reducers/chat-reducer', () => ({
  chatReducer: mockChatReducer,
  initialChatState: mockInitialChatState,
}))

vi.mock('@/lib/api/chat', () => ({
  sendMessage: (...args: any[]) => mockSendMessage(...args),
}))

import { useChat } from '@/hooks/use-chat'
import type { ChatContext } from '@/lib/chat'

// localStorage mock
beforeEach(() => {
  chatStorage.clear()
  Object.defineProperty(window, 'localStorage', {
    value: {
      getItem: vi.fn((key: string) => chatStorage.get(key) ?? null),
      setItem: vi.fn((key: string, value: string) => chatStorage.set(key, value)),
      removeItem: vi.fn((key: string) => chatStorage.delete(key)),
    },
    writable: true,
  })
})

const context: ChatContext = {
  profile: {
    birthDate: { day: '14', month: '07', year: '1995' },
    birthTime: { hours: '08', minutes: '42', unknown: false },
    birthPlace: 'Киев, Украина',
    currentCity: 'Лиссабон, Португалия',
    birthdayCity: 'Лиссабон, Португалия',
    sameAsBirth: false,
    birthdaySameAsCurrent: true,
    gender: 'male',
  },
}

describe('useChat', () => {
  it('starts with empty messages and hydration triggers', async () => {
    const { result } = renderHook(() => useChat(context))

    await waitFor(() => {
      expect(result.current.loaded).toBe(true)
    })
    expect(result.current.messages).toEqual([])
    expect(result.current.pending).toBe(false)
  })

  it('hydrates messages from localStorage on mount', async () => {
    const saved: ChatMessage[] = [
      { id: 'm1', role: 'user', content: 'Hi', createdAt: Date.now() },
    ]
    chatStorage.set('lumen:chat', JSON.stringify(saved))

    const { result } = renderHook(() => useChat(context))

    await waitFor(() => {
      expect(result.current.loaded).toBe(true)
    })
    expect(result.current.messages).toEqual(saved)
  })

  it('ignores invalid JSON in localStorage', async () => {
    chatStorage.set('lumen:chat', 'not-json')

    const { result } = renderHook(() => useChat(context))

    await waitFor(() => {
      expect(result.current.loaded).toBe(true)
    })
    expect(result.current.messages).toEqual([])
  })

  it('does not send empty messages', async () => {
    const { result } = renderHook(() => useChat(context))

    await act(async () => {
      await result.current.send('   ')
    })
    expect(mockSendMessage).not.toHaveBeenCalled()
  })

  it('sends message and receives streamed tokens', async () => {
    mockSendMessage.mockImplementationOnce(async function* () {
      yield 'Hello world'
    })

    const { result } = renderHook(() => useChat(context))

    await act(async () => {
      await result.current.send('Hi agent')
    })

    expect(result.current.pending).toBe(false)
    const msgs = result.current.messages
    const userMsg = msgs.find((m) => m.role === 'user')
    expect(userMsg?.content).toBe('Hi agent')
    const assistantMsg = msgs.find((m) => m.role === 'assistant')
    expect(assistantMsg?.content).toBe('Hello world')
  })

  it('pending becomes false after send completes', async () => {
    mockSendMessage.mockImplementationOnce(async function* () {
      yield 'one'
    })

    const { result } = renderHook(() => useChat(context))

    await act(async () => {
      await result.current.send('test')
    })
    expect(result.current.pending).toBe(false)
  })

  it('handles AbortError through stop gracefully', async () => {
    mockSendMessage.mockImplementationOnce(async function* () {
      yield 'tick1'
      yield 'tick2'
      const err = new DOMException('Aborted', 'AbortError')
      throw err
    })

    const { result } = renderHook(() => useChat(context))

    await act(async () => {
      await result.current.send('test')
    })

    expect(result.current.pending).toBe(false)
  })

  it('reset clears messages', async () => {
    const saved: ChatMessage[] = [
      { id: 'm1', role: 'user', content: 'old', createdAt: Date.now() },
    ]
    chatStorage.set('lumen:chat', JSON.stringify(saved))

    const { result } = renderHook(() => useChat(context))
    await waitFor(() => {
      expect(result.current.loaded).toBe(true)
    })

    act(() => result.current.reset())
    expect(result.current.messages).toHaveLength(0)
  })

  it('handles fetch error gracefully', async () => {
    mockSendMessage.mockImplementationOnce(async function* () {
      throw new Error('Network error')
    })

    const { result } = renderHook(() => useChat(context))

    await act(async () => {
      await result.current.send('test')
    })

    const msgs = result.current.messages
    expect(msgs.length).toBe(2)
    expect(msgs[1].role).toBe('assistant')
    expect(msgs[1].content).toContain('Не получилось получить ответ')
  })

  it('saves messages to localStorage after send', async () => {
    mockSendMessage.mockImplementationOnce(async function* () {
      yield 'streamed content'
    })

    const { result } = renderHook(() => useChat(context))

    await act(async () => {
      await result.current.send('hello')
    })

    expect(chatStorage.has('lumen:chat')).toBe(true)
    const stored = JSON.parse(chatStorage.get('lumen:chat')!)
    expect(Array.isArray(stored)).toBe(true)
    expect(stored.length).toBeGreaterThanOrEqual(1)
  })
})
