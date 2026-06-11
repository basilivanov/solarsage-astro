
// ############################################################################
// AI_HEADER: MODULE_REDUCERS_CHAT_REDUCER
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/reducers/chat-reducer.ts
// owns:
//   - lib/reducers/chat-reducer.ts
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

/**
 * Чистый reducer для чата — вся бизнес-логика переходов без side-effects.
 *
 * Преимущества:
 *  - тестируется без jsdom, RTL, таймеров;
 *  - события соответствуют реальным бизнес-событиям (user_sent, token, done...);
 *  - UI-хук (`useChat`) становится тонкой оболочкой, которая
 *    конвертирует React-эффекты в события редьюсера.
 */

import type { ChatMessage } from "@/lib/contracts/chat"

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

export interface ChatState {
  messages: ChatMessage[]
  /** Запрос в полёте (от отправки до done/aborted/error) */
  pending: boolean
  /** ID сообщения, в которое сейчас докидываем токены */
  streamingId: string | null
  /** Данные загружены из storage */
  hydrated: boolean
}

export const initialChatState: ChatState = {
  messages: [],
  pending: false,
  streamingId: null,
  hydrated: false,
}

// ---------------------------------------------------------------------------
// Events
// ---------------------------------------------------------------------------

export type ChatEvent =
  | { type: "hydrated"; messages: ChatMessage[] }
  | { type: "user_sent"; id: string; text: string; createdAt: number }
  | { type: "stream_started"; id: string; createdAt: number }
  | { type: "token"; id: string; content: string }
  | { type: "done"; id: string }
  | { type: "aborted"; id: string }
  | { type: "error"; message: ChatMessage }
  | { type: "reset" }

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

export function chatReducer(state: ChatState, event: ChatEvent): ChatState {
  switch (event.type) {
    case "hydrated":
      return {
        ...state,
        messages: event.messages,
        hydrated: true,
      }

    case "user_sent": {
      // Игнорируем двойные send
      if (state.pending) return state

      const userMsg: ChatMessage = {
        id: event.id,
        role: "user",
        content: event.text,
        createdAt: event.createdAt,
      }
      return {
        ...state,
        messages: [...state.messages, userMsg],
        pending: true,
      }
    }

    case "stream_started": {
      const assistantMsg: ChatMessage = {
        id: event.id,
        role: "assistant",
        content: "",
        createdAt: event.createdAt,
      }
      return {
        ...state,
        messages: [...state.messages, assistantMsg],
        streamingId: event.id,
      }
    }

    case "token": {
      // Игнорируем токены для другого стрима
      if (state.streamingId !== event.id) return state

      return {
        ...state,
        messages: state.messages.map((m) =>
          m.id === event.id ? { ...m, content: event.content } : m
        ),
      }
    }

    case "done":
    case "aborted": {
      // Оставляем то, что успели налить
      return {
        ...state,
        pending: false,
        streamingId: null,
      }
    }

    case "error": {
      return {
        ...state,
        messages: [...state.messages, event.message],
        pending: false,
        streamingId: null,
      }
    }

    case "reset":
      return {
        ...initialChatState,
        hydrated: true, // сохраняем hydrated, чтобы не было re-hydration
      }

    default:
      return state
  }
}

// ---------------------------------------------------------------------------
// Selectors (для удобства тестирования)
// ---------------------------------------------------------------------------

export function selectLastMessage(state: ChatState): ChatMessage | undefined {
  return state.messages[state.messages.length - 1]
}

export function selectIsStreaming(state: ChatState): boolean {
  return state.streamingId !== null
}

export function selectCanSend(state: ChatState): boolean {
  return !state.pending
}
