import { z } from "zod"
import {
  ParagraphBlockSchema,
  LeadBlockSchema,
  HeadingBlockSchema,
  ListBlockSchema,
  CalloutBlockSchema,
  ProsConsBlockSchema,
  DividerBlockSchema,
} from "@/lib/contracts/natal"

// QuoteBlock in horary is defined separately to support backend "source" field
export const HoraryQuoteBlockSchema = z.object({
  type: z.literal("quote"),
  text: z.string().min(1),
  source: z.string().optional(),
})

// ---- Хорарные блоки (НОВЫЕ) ----

export const VerdictCardBlockSchema = z.object({
  type: z.literal("verdict_card"),
  verdict: z.enum(["yes", "no", "maybe"]),
  confidence: z.number().min(0).max(1),
  label: z.string().optional(),
})

export const TimingBlockSchema = z.object({
  type: z.literal("timing"),
  timeRange: z.string().min(1),
  text: z.string().optional(),
})

// ---- Расширенный Block union для хорара ----

export const HoraryBlockSchema = z.discriminatedUnion("type", [
  ParagraphBlockSchema,
  LeadBlockSchema,
  HeadingBlockSchema,
  ListBlockSchema,
  CalloutBlockSchema,
  ProsConsBlockSchema,
  DividerBlockSchema,
  HoraryQuoteBlockSchema,
  VerdictCardBlockSchema,
  TimingBlockSchema,
])

// ---- Категории и схемы запросов/ответов ----

export const HoraryCategorySchema = z.enum([
  "love", "career", "money", "health", "travel", "other"
])

export const HoraryQuestionCreateSchema = z.object({
  text: z.string().min(5).max(500),
  category: HoraryCategorySchema.optional(),
  clientTimezone: z.string(),
  clientLocalTime: z.string().optional(),
  questionLat: z.number().optional(),
  questionLon: z.number().optional(),
})

export const HoraryAnswerSchema = z.object({
  verdict: z.enum(["yes", "no", "maybe"]),
  confidence: z.number(),
  blocks: z.array(HoraryBlockSchema),
  planets: z.array(z.string()),
  generatedAt: z.string(),
})

export const HoraryQuestionSchema = z.object({
  id: z.string(),
  text: z.string(),
  category: HoraryCategorySchema.optional().nullable(),
  status: z.enum(["pending", "processing", "answered", "expired"]),
  clientTimezone: z.string(),
  clientLocalTime: z.string().optional().nullable(),
  createdAt: z.string(),
  answer: HoraryAnswerSchema.optional().nullable(),
})

export const HoraryQuotaSchema = z.object({
  left: z.number(),
  nextInDays: z.number(),
  canPurchase: z.boolean(),
})

// ---- Типы ----

export type HoraryCategory = z.infer<typeof HoraryCategorySchema>
export type HoraryQuestionCreate = z.infer<typeof HoraryQuestionCreateSchema>
export type HoraryBlock = z.infer<typeof HoraryBlockSchema>
export type VerdictCardBlock = z.infer<typeof VerdictCardBlockSchema>
export type TimingBlock = z.infer<typeof TimingBlockSchema>
export type HoraryAnswer = z.infer<typeof HoraryAnswerSchema>
export type HoraryQuestion = z.infer<typeof HoraryQuestionSchema>
export type HoraryQuota = z.infer<typeof HoraryQuotaSchema>

// ---- Категории для формы ----

export const HORARY_CATEGORIES: {
  key: HoraryCategory
  label: string
  emoji: string
  placeholder: string
}[] = [
  { key: "love", label: "Отношения", emoji: "💕", placeholder: "Выйду ли я замуж в этом году?" },
  { key: "career", label: "Работа", emoji: "💼", placeholder: "Стоит ли мне менять работу в этом месяце?" },
  { key: "money", label: "Деньги", emoji: "💰", placeholder: "Будет ли у меня доход от этого проекта?" },
  { key: "health", label: "Здоровье", emoji: "🏥", placeholder: "Пройдёт ли болезнь к концу месяца?" },
  { key: "travel", label: "Переезд", emoji: "✈️", placeholder: "Удачным ли будет переезд в новый город?" },
  { key: "other", label: "Другое", emoji: "⚡", placeholder: "Найду ли я потерянную вещь?" },
]
