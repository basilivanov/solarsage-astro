// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_ELECTION
// ROLE: UI — election contracts & zod schemas v2
// DEPENDENCIES: zod
// ############################################################################

import { z } from "zod"

export type ElectionSubCategory = {
  key: string
  label: string
}

export type ElectionCategory = {
  key: string
  label: string
  emoji: string
  subs: ElectionSubCategory[]
}

export const ELECTION_CATEGORIES: readonly ElectionCategory[] = [
  {
    key: "relations",
    label: "Отношения",
    emoji: "💕",
    subs: [
      { key: "date", label: "Свидание" },
      { key: "wedding", label: "Свадьба/помолвка" },
      { key: "reconcile", label: "Примирение" },
    ],
  },
  {
    key: "work",
    label: "Работа и дела",
    emoji: "💼",
    subs: [
      { key: "job", label: "Новая работа" },
      { key: "launch", label: "Запуск проекта" },
      { key: "contract", label: "Документы и договоры" },
    ],
  },
  {
    key: "travel",
    label: "Поездки",
    emoji: "🛫",
    subs: [
      { key: "leisure", label: "Путешествие/отдых" },
      { key: "business", label: "Деловая поездка" },
      { key: "family", label: "Поездка к родным" },
    ],
  },
  {
    key: "money",
    label: "Покупки и финансы",
    emoji: "🛍",
    subs: [
      { key: "purchase", label: "Крупная покупка" },
      { key: "invest", label: "Вложения и финрешения" },
    ],
  },
  {
    key: "beauty",
    label: "Красота и тело",
    emoji: "💇‍♀️",
    subs: [
      { key: "salon", label: "Стрижка/салон" },
      { key: "treatment", label: "Процедуры и лечение" },
    ],
  },
  {
    key: "family",
    label: "Семья и дом",
    emoji: "👶",
    subs: [
      { key: "conception", label: "Зачатие ребёнка" },
      { key: "moving", label: "Переезд/новоселье" },
    ],
  },
] as const

export const ElectionDayFactSchema = z.object({
  date: z.string(),
  score: z.number(),
  label: z.enum(["great", "good", "ok", "avoid"]),
  reasons: z.array(z.string()),
  moon_sign: z.string().optional(),
  moon_sign_ru: z.string().optional(),
  waxing: z.boolean().optional(),
  phase_pct: z.number().optional(),
  voc_fraction: z.number().optional(),
  voc_intervals: z.array(z.string()).optional(),
  mercury_retro: z.boolean().optional(),
})

export type ElectionDayFact = z.infer<typeof ElectionDayFactSchema>

export const ElectionNarrativeNoteSchema = z.object({
  date: z.string(),
  note: z.string(),
})

export const ElectionNarrativeSchema = z.object({
  hero_reason: z.string(),
  hero_personal: z.string(),
  hero_plain: z.string(),
  hero_hours: z.string(),
  day_notes: z.array(ElectionNarrativeNoteSchema),
  avoid_notes: z.array(ElectionNarrativeNoteSchema),
})

export type ElectionNarrative = z.infer<typeof ElectionNarrativeSchema>

export const ElectionResultFactsSchema = z.object({
  event: z.object({
    category: z.string().optional(),
    sub: z.string().optional(),
    label: z.string().optional(),
  }).optional(),
  personal: z.object({
    natal_moon_sign: z.string().nullable().optional(),
    natal_moon_sign_ru: z.string().nullable().optional(),
    resonates: z.boolean().optional(),
  }).optional(),
})

export type ElectionResultFacts = z.infer<typeof ElectionResultFactsSchema>

export const ElectionResultSchema = z.object({
  event: z.string(),
  best_days: z.array(ElectionDayFactSchema),
  avoid_days: z.array(ElectionDayFactSchema),
  days: z.array(ElectionDayFactSchema).optional(),
  facts: ElectionResultFactsSchema.optional(),
  narrative: ElectionNarrativeSchema.optional(),
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
