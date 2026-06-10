/**
 * Тесты reducer'а чата — чистая бизнес-логика без jsdom.
 */

import { describe, it, expect } from "vitest"

import {
  chatReducer,
  initialChatState,
  selectLastMessage,
  selectIsStreaming,
  selectCanSend,
  type ChatState,
} from "@/lib/reducers/chat-reducer"

describe("chatReducer", () => {
  describe("hydrated", () => {
    it("sets messages and hydrated flag", () => {
      const messages = [
        { id: "1", role: "user" as const, content: "Hi", createdAt: Date.now() },
      ]
      const next = chatReducer(initialChatState, { type: "hydrated", messages })
      expect(next.messages).toEqual(messages)
      expect(next.hydrated).toBe(true)
    })
  })

  describe("user_sent", () => {
    it("adds user message and sets pending", () => {
      const now = Date.now()
      const next = chatReducer(initialChatState, {
        type: "user_sent",
        id: "msg-1",
        text: "Hello",
        createdAt: now,
      })

      expect(next.messages).toHaveLength(1)
      expect(next.messages[0].role).toBe("user")
      expect(next.messages[0].content).toBe("Hello")
      expect(next.pending).toBe(true)
    })

    it("ignores if already pending", () => {
      const pendingState: ChatState = { ...initialChatState, pending: true }
      const next = chatReducer(pendingState, {
        type: "user_sent",
        id: "msg-2",
        text: "Another",
        createdAt: Date.now(),
      })
      expect(next.messages).toHaveLength(0)
    })
  })

  describe("stream_started", () => {
    it("adds empty assistant message and sets streamingId", () => {
      const now = Date.now()
      const next = chatReducer(initialChatState, {
        type: "stream_started",
        id: "assistant-1",
        createdAt: now,
      })

      expect(next.messages).toHaveLength(1)
      expect(next.messages[0].role).toBe("assistant")
      expect(next.messages[0].content).toBe("")
      expect(next.streamingId).toBe("assistant-1")
    })
  })

  describe("token", () => {
    it("updates streaming message content", () => {
      const state: ChatState = {
        ...initialChatState,
        messages: [
          { id: "assistant-1", role: "assistant", content: "Hello", createdAt: Date.now() },
        ],
        streamingId: "assistant-1",
      }
      const next = chatReducer(state, {
        type: "token",
        id: "assistant-1",
        content: "Hello world",
      })

      expect(next.messages[0].content).toBe("Hello world")
    })

    it("ignores token for different id", () => {
      const state: ChatState = {
        ...initialChatState,
        messages: [
          { id: "assistant-1", role: "assistant", content: "Hello", createdAt: Date.now() },
        ],
        streamingId: "assistant-1",
      }
      const next = chatReducer(state, {
        type: "token",
        id: "different-id",
        content: "Should not apply",
      })

      expect(next.messages[0].content).toBe("Hello")
    })
  })

  describe("done", () => {
    it("clears pending and streamingId", () => {
      const state: ChatState = {
        ...initialChatState,
        pending: true,
        streamingId: "assistant-1",
      }
      const next = chatReducer(state, { type: "done", id: "assistant-1" })

      expect(next.pending).toBe(false)
      expect(next.streamingId).toBeNull()
    })
  })

  describe("error", () => {
    it("adds error message and clears pending", () => {
      const state: ChatState = { ...initialChatState, pending: true }
      const errorMsg = {
        id: "error-1",
        role: "assistant" as const,
        content: "Error occurred",
        createdAt: Date.now(),
      }
      const next = chatReducer(state, { type: "error", message: errorMsg })

      expect(next.messages).toHaveLength(1)
      expect(next.pending).toBe(false)
    })
  })

  describe("reset", () => {
    it("resets to initial state but keeps hydrated", () => {
      const state: ChatState = {
        messages: [{ id: "1", role: "user", content: "Hi", createdAt: Date.now() }],
        pending: true,
        streamingId: "x",
        hydrated: true,
      }
      const next = chatReducer(state, { type: "reset" })

      expect(next.messages).toHaveLength(0)
      expect(next.pending).toBe(false)
      expect(next.streamingId).toBeNull()
      expect(next.hydrated).toBe(true)
    })
  })

  describe("selectors", () => {
    it("selectLastMessage returns last message", () => {
      const state: ChatState = {
        ...initialChatState,
        messages: [
          { id: "1", role: "user", content: "First", createdAt: 1 },
          { id: "2", role: "assistant", content: "Second", createdAt: 2 },
        ],
      }
      expect(selectLastMessage(state)?.content).toBe("Second")
    })

    it("selectIsStreaming returns true when streaming", () => {
      const state: ChatState = { ...initialChatState, streamingId: "x" }
      expect(selectIsStreaming(state)).toBe(true)
    })

    it("selectCanSend returns false when pending", () => {
      const state: ChatState = { ...initialChatState, pending: true }
      expect(selectCanSend(state)).toBe(false)
    })
  })
})
