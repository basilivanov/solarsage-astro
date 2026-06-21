
// ############################################################################
// AI_HEADER: MODULE_API_CHAT
// ROLE: Tests — chat.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ####// START_MODULE_CONTRACT
// purpose: Tests for chat.ts behavior
// owns:
//   - lib/api/chat.ts
// inputs: Endpoint params, request body
// outputs: Parsed response / typed data
// dependencies: local modules
// side_effects: Network calls to API
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * API-фасад чата.
 *
 * Единственная точка интеграции с ИИ. UI и хук `useChat` зовут только её.
 * Использует реальные backend-эндпоинты.
 */

import type { ChatContext, ChatMessage } from "@/lib/contracts/chat"
import { IS_DEMO_MODE } from "@/lib/demo-mode"
import { DEMO_CHAT_MESSAGES } from "@/lib/demo-data"

export type { ChatContext, ChatMessage }

export async function* sendMessage(args: {
  history: ChatMessage[]
  message: string
  context: ChatContext
  signal?: AbortSignal
}): AsyncGenerator<string, void, unknown> {
  if (IS_DEMO_MODE) {
    const reply = DEMO_CHAT_MESSAGES.find(m => m.role === "assistant")?.text
      || "Я твой астрологический ассистент. Спрашивай о дне, отношениях, карьере — я помогу разобраться!"
    // Simulate streaming — yield word by word
    const words = reply.split(" ")
    for (let i = 0; i < words.length; i++) {
      yield (i === 0 ? "" : " ") + words[i]
      await new Promise(r => setTimeout(r, 30))
    }
    return
  }

  const createRes = await fetch("/api/chat/threads", {
    method: "POST",
    credentials: "include",
    headers: { "Accept": "application/json" },
    signal: args.signal,
  })
  if (!createRes.ok) {
    throw new Error(`Failed to create chat thread: ${createRes.status}`)
  }
  const { id: threadId } = await createRes.json()

  const msgRes = await fetch(`/api/chat/threads/${threadId}/messages`, {
    method: "POST",
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json",
    },
    body: JSON.stringify({ content: args.message }),
    signal: args.signal,
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
