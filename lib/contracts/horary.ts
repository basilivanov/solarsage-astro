
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_HORARY
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/contracts/horary.ts
// owns:
//   - lib/contracts/horary.ts
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
  confidenceLabel: z.enum(["low", "medium", "high"]),
  confidenceExplanation: z.string(),
})

export const TestimonyItemSchema = z.object({
  title: z.string(),
  explanation: z.string(),
  weight: z.number(),
  planets: z.array(z.string()).default([]),
  aspectType: z.string().optional().nullable(),
  orb: z.number().optional().nullable(),
})

export const TestimoniesBlockSchema = z.object({
  type: z.literal("testimonies"),
  prosLabel: z.string().default('Свидетельства «за»'),
  consLabel: z.string().default('Свидетельства «против»'),
  neutralLabel: z.string().default("Нейтральные факторы"),
  pros: z.array(TestimonyItemSchema).default([]),
  cons: z.array(TestimonyItemSchema).default([]),
  neutral: z.array(TestimonyItemSchema).default([]),
})

export const TimingBlockSchema = z.object({
  type: z.literal("timing"),
  status: z.enum(["known", "unclear", "not_enough_evidence"]),
  timeRange: z.string().optional().nullable(),
  text: z.string(),
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
  TestimoniesBlockSchema,
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
  questionLocationName: z.string().optional(),
  idempotencyKey: z.string().min(1),
})

export const HoraryAnswerSchema = z.object({
  verdict: z.enum(["yes", "no", "maybe"]),
  confidence: z.number(),
  confidenceLabel: z.enum(["low", "medium", "high"]).default("medium"),
  confidenceExplanation: z.string().default(""),
  blocks: z.array(HoraryBlockSchema),
  planets: z.array(z.string()),
  generatedAt: z.string(),
})

export const HoraryQuestionSchema = z.object({
  id: z.string(),
  text: z.string(),
  category: HoraryCategorySchema.optional().nullable(),
  status: z.enum(["pending", "processing", "answered", "failed", "refunded", "expired"]),
  spentCreditSource: z.enum(["subscription_weekly_free", "referral_bonus", "gift", "paid", "adjustment"]).optional().nullable(),
  creditRefunded: z.boolean().default(false),
  clientTimezone: z.string(),
  clientLocalTime: z.string().optional().nullable(),
  questionLocationName: z.string().optional().nullable(),
  createdAt: z.string(),
  answer: HoraryAnswerSchema.optional().nullable(),
})

export const HoraryQuotaSchema = z.object({
  weeklyFreeAvailable: z.boolean(),
  weeklyFreeExpiresAt: z.string().optional().nullable(),
  nextWeeklyFreeAt: z.string().optional().nullable(),
  bonusCredits: z.number(),
  paidCredits: z.number(),
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
