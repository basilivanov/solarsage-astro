
// ############################################################################
// AI_HEADER: FRONTEND_API_CHAT — thread creation and assistant-message transport.
// ROLE: Single chat integration facade consumed by use-chat.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-CHAT
// purpose: Create a backend thread, send one user message and yield assistant content.
// owns:
//   - lib/api/chat.ts
// inputs: history, message, context and optional AbortSignal; history/context remain compatibility inputs.
// outputs: AsyncGenerator yielding zero or one assistant content string.
// dependencies: lib/contracts/chat; fetch; JSON.
// side_effects: credentialed POST /api/chat/threads, then POST its messages endpoint.
// emitted_logs: none.
// invariants:
//   - AbortSignal is passed to both requests.
//   - Message body retains the existing { content } shape.
//   - snake_case or camelCase assistant message is accepted.
//   - The generator yields only when assistant content exists.
// failure_policy: Throw the existing status-bearing Error before yielding when either request is non-ok; network and abort errors propagate.
// END_MODULE_CONTRACT: M-FRONTEND-API-CHAT

// START_MODULE_MAP: M-FRONTEND-API-CHAT
// public_entrypoints:
//   - ChatContext
//   - ChatMessage
//   - sendMessage
// semantic_blocks:
//   - THREAD_CREATE: create an authenticated backend thread.
//   - MESSAGE_SEND: send the current message to the new thread.
//   - ASSISTANT_YIELD: accept wire naming variants and yield existing content.
// owned_tests:
//   - __tests__/hooks/useChat.test.ts
// END_MODULE_MAP: M-FRONTEND-API-CHAT
/**
 * API-фасад чата.
 *
 * Единственная точка интеграции с ИИ. UI и хук `useChat` зовут только её.
 * Использует реальные backend-эндпоинты.
 */

import type { ChatContext, ChatMessage } from "@/lib/contracts/chat"
import { instrumentedFetch } from "@/lib/log/instrumented-fetch"

export type { ChatContext, ChatMessage }

export async function* sendMessage(args: {
  history: ChatMessage[]
  message: string
  context: ChatContext
  signal?: AbortSignal
}): AsyncGenerator<string, void, unknown> {
  const createRes = await instrumentedFetch({
    operation: "chat.create_thread",
    routeTemplate: "POST /api/chat/threads",
    url: "/api/chat/threads",
    init: {
      method: "POST",
      credentials: "include",
      headers: { "Accept": "application/json" },
      signal: args.signal,
    },
  })
  if (!createRes.ok) {
    throw new Error(`Failed to create chat thread: ${createRes.status}`)
  }
  const { id: threadId } = await createRes.json()

  const msgRes = await instrumentedFetch({
    operation: "chat.send_message",
    routeTemplate: "POST /api/chat/threads/{id}/messages",
    url: `/api/chat/threads/${threadId}/messages`,
    init: {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        "Accept": "application/json",
      },
      body: JSON.stringify({ content: args.message }),
      signal: args.signal,
    },
  })
  if (!msgRes.ok) {
    throw new Error(`Failed to send message: ${msgRes.status}`)
  }
  const body = await msgRes.json()

  const assistantMsg = body.assistant_message ?? body.assistantMessage
  if (assistantMsg?.content) {
    yield assistantMsg.content
  }
}
