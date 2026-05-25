/**
 * Zod-контракт для Chat (чат с ассистентом).
 *
 * Единственный источник правды о форме данных чата.
 */

import { z } from "zod"
import { ProfileSchema } from "./profile"

export const ChatRoleSchema = z.enum(["user", "assistant"])

export const ChatMessageSchema = z.object({
  id: z.string().min(1),
  role: ChatRoleSchema,
  content: z.string(),
  /** Unix ms — храним именно число, чтобы сериализовать в localStorage. */
  createdAt: z.number().int().positive(),
})

export const ChatContextSchema = z.object({
  profile: ProfileSchema,
})

export const ChatHistorySchema = z.array(ChatMessageSchema)

export type ChatRole = z.infer<typeof ChatRoleSchema>
export type ChatMessage = z.infer<typeof ChatMessageSchema>
export type ChatContext = z.infer<typeof ChatContextSchema>

/**
 * Валидирует ChatMessage и выбрасывает при несоответствии.
 */
export function validateChatMessage(data: unknown): ChatMessage {
  return ChatMessageSchema.parse(data)
}

/**
 * Валидирует массив сообщений.
 */
export function validateChatHistory(data: unknown): ChatMessage[] {
  return ChatHistorySchema.parse(data)
}

/**
 * Безопасная валидация истории — для загрузки из localStorage.
 */
export function safeValidateChatHistory(data: unknown) {
  return ChatHistorySchema.safeParse(data)
}
