/**
 * API-фасад чата.
 *
 * Единственная точка интеграции с ИИ. UI и хук `useChat` зовут только её.
 * Переключение между fixtures и реальным API — через ENV.
 *
 * Когда подключим AI SDK:
 *
 *   const result = streamText({
 *     model,
 *     system: buildContextSummary(args.context.profile),
 *     messages: args.history.map(...),
 *     abortSignal: args.signal,
 *   })
 *   yield* result.textStream
 */

import type { ChatContext, ChatMessage } from "@/lib/contracts/chat"
import { USE_FIXTURES } from "./config"

export type { ChatContext, ChatMessage }

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export async function* sendMessage(args: {
  history: ChatMessage[]
  message: string
  context: ChatContext
  signal?: AbortSignal
}): AsyncGenerator<string, void, unknown> {
  if (USE_FIXTURES) {
    const { sendMessageFixture } = await import("./chat.fixtures")
    yield* sendMessageFixture(args)
    return
  }

  // Production stub — будет заменён на AI SDK интеграцию
  // TODO: Implement real AI integration
  //
  // const result = streamText({
  //   model: openai("gpt-4"),
  //   system: buildContextSummary(args.context.profile),
  //   messages: args.history.map(m => ({ role: m.role, content: m.content })),
  //   abortSignal: args.signal,
  // })
  // for await (const chunk of result.textStream) {
  //   yield chunk
  // }

  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}
