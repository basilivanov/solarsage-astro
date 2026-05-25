/**
 * Fixture-реализация для chat API.
 * Используется только в dev/storybook/e2e.
 * В production путь сюда недостижим (tree-shake).
 */

import type { ChatContext, ChatMessage } from "@/lib/contracts/chat"
import { streamMockReply } from "@/lib/mocks/chat"

export async function* sendMessageFixture(args: {
  history: ChatMessage[]
  message: string
  context: ChatContext
  signal?: AbortSignal
}): AsyncGenerator<string, void, unknown> {
  yield* streamMockReply({ message: args.message, signal: args.signal })
}
