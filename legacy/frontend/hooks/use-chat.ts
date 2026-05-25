"use client"

import { useCallback, useEffect, useReducer, useRef } from "react"

import { type ChatContext, type ChatMessage } from "@/lib/chat"
import { sendMessage } from "@/lib/api/chat"
import { STORAGE_KEYS } from "@/lib/storage-keys"
import {
  chatReducer,
  initialChatState,
  type ChatEvent,
} from "@/lib/reducers/chat-reducer"

/**
 * Стейт-хук для чата с агентом.
 *
 * Теперь это тонкая обёртка над чистым `chatReducer`:
 *  - reducer содержит всю бизнес-логику (тестируется без jsdom);
 *  - хук отвечает только за side-effects: persistence, stream, abort.
 */
export function useChat(context: ChatContext) {
  const [state, dispatch] = useReducer(chatReducer, initialChatState)
  const abortRef = useRef<AbortController | null>(null)

  // Гидратация из localStorage один раз на маунте
  useEffect(() => {
    dispatch({ type: "hydrated", messages: loadFromStorage() })
  }, [])

  // Сохраняем только после гидратации
  useEffect(() => {
    if (!state.hydrated) return
    saveToStorage(state.messages)
  }, [state.messages, state.hydrated])

  // Гасим висящий запрос при размонтировании
  useEffect(() => {
    return () => {
      abortRef.current?.abort()
    }
  }, [])

  const send = useCallback(
    async (raw: string) => {
      const text = raw.trim()
      if (!text || state.pending) return

      const userId = makeId()
      const now = Date.now()

      dispatch({ type: "user_sent", id: userId, text, createdAt: now })

      const ctrl = new AbortController()
      abortRef.current = ctrl

      const assistantId = makeId()
      let assistantStarted = false
      let buffer = ""

      try {
        // Формируем историю с новым сообщением
        const userMsg: ChatMessage = {
          id: userId,
          role: "user",
          content: text,
          createdAt: now,
        }
        const history = [...state.messages, userMsg]

        const stream = sendMessage({
          history,
          message: text,
          context,
          signal: ctrl.signal,
        })

        for await (const chunk of stream) {
          if (ctrl.signal.aborted) break
          buffer += chunk

          if (!assistantStarted) {
            assistantStarted = true
            dispatch({
              type: "stream_started",
              id: assistantId,
              createdAt: Date.now(),
            })
          }

          dispatch({ type: "token", id: assistantId, content: buffer })
        }

        if (!ctrl.signal.aborted) {
          dispatch({ type: "done", id: assistantId })
        }
      } catch (err) {
        if ((err as DOMException | undefined)?.name === "AbortError") {
          dispatch({ type: "aborted", id: assistantId })
          return
        }

        const failMsg: ChatMessage = {
          id: makeId(),
          role: "assistant",
          content:
            "Не получилось получить ответ. Попробуй ещё раз через минуту.",
          createdAt: Date.now(),
        }
        dispatch({ type: "error", message: failMsg })
      } finally {
        if (abortRef.current === ctrl) {
          abortRef.current = null
        }
      }
    },
    [state.messages, state.pending, context]
  )

  const stop = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    dispatch({ type: "reset" })
  }, [])

  return {
    messages: state.messages,
    pending: state.pending,
    streamingId: state.streamingId,
    loaded: state.hydrated,
    send,
    stop,
    reset,
  }
}

// --- helpers ---------------------------------------------------------------

function loadFromStorage(): ChatMessage[] {
  if (typeof window === "undefined") return []
  try {
    const raw = window.localStorage.getItem(STORAGE_KEYS.chat)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(isMessage)
  } catch {
    return []
  }
}

function saveToStorage(messages: ChatMessage[]) {
  if (typeof window === "undefined") return
  try {
    window.localStorage.setItem(STORAGE_KEYS.chat, JSON.stringify(messages))
  } catch {
    /* quota / private mode — игнорируем, это не критично для UX */
  }
}

function isMessage(v: unknown): v is ChatMessage {
  if (!v || typeof v !== "object") return false
  const o = v as Record<string, unknown>
  return (
    typeof o.id === "string" &&
    (o.role === "user" || o.role === "assistant") &&
    typeof o.content === "string" &&
    typeof o.createdAt === "number"
  )
}

function makeId() {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`
}
