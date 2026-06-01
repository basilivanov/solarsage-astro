/**
 * API-фасад чата.
 *
 * Единственная точка интеграции с ИИ. UI и хук `useChat` зовут только её.
 * Использует реальные backend-эндпоинты.
 */

import type { ChatContext, ChatMessage } from "@/lib/contracts/chat"

export type { ChatContext, ChatMessage }

export async function* sendMessage(args: {
  history: ChatMessage[]
  message: string
  context: ChatContext
  signal?: AbortSignal
}): AsyncGenerator<string, void, unknown> {
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
