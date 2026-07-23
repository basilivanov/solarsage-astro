// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_ELECTION
// ROLE: UI — election contracts & zod schemas
// DEPENDENCIES: zod
// ############################################################################

import { z } from "zod"

export const ELECTION_EVENTS = [
  { key: "date", label: "Свидание", emoji: "💕" },
  { key: "wedding", label: "Свадьба/помолвка", emoji: "💍" },
  { key: "job", label: "Собеседование/новая работа", emoji: "💼" },
  { key: "contract", label: "Подписание документов", emoji: "✍️" },
  { key: "beauty", label: "Стрижка/салон", emoji: "💇‍♀️" },
  { key: "travel", label: "Поездка/переезд", emoji: "🛫" },
  { key: "purchase", label: "Крупная покупка", emoji: "🛍" },
  { key: "launch", label: "Запуск проекта", emoji: "🚀" },
  { key: "money", label: "Финансовые решения", emoji: "💰" },
] as const

export type ElectionEventKey = (typeof ELECTION_EVENTS)[number]["key"]

export const ElectionDayReasonSchema = z.object({
  date: z.string(),
  score: z.number(),
  label: z.enum(["great", "good", "ok", "avoid"]),
  reasons: z.array(z.string()),
})

export type ElectionDayReason = z.infer<typeof ElectionDayReasonSchema>

export const ElectionResultSchema = z.object({
  event: z.string(),
  best_days: z.array(ElectionDayReasonSchema),
  avoid_days: z.array(ElectionDayReasonSchema),
})

export type ElectionResult = z.infer<typeof ElectionResultSchema>

export const ElectionSearchSchema = z.object({
  id: z.string().uuid(),
  eventType: z.string(),
  windowFrom: z.string(),
  windowTo: z.string(),
  status: z.enum(["pending", "processing", "done", "failed", "refunded"]),
  createdAt: z.string(),
  result: ElectionResultSchema.nullable().optional(),
  publicErrorCode: z.string().nullable().optional(),
  publicErrorMessage: z.string().nullable().optional(),
})

export type ElectionSearch = z.infer<typeof ElectionSearchSchema>
