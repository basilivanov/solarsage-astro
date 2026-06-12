
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_NATAL
// ROLE: UI — natal
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI natal — component
// owns:
//   - lib/contracts/natal.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * Zod-контракт для Natal (натальный отчёт).
 *
 * Единственный источник правды о форме данных натального отчёта на фронте.
 * Версионирован: schemaVersion позволяет фронту держать несколько
 * рендереров параллельно.
 *
 * Wave 5: добавлены типы, выровненные с backend Pydantic-схемами:
 *   - NatalReportRead — ответ GET /api/natal/report/{id}
 *   - NatalGenerateResponse — ответ POST /api/natal/generate
 *   - ProsConsItem — {title, text} вместо plain string
 *   - Callout tone выровнен с backend: info | warning | insight | positive
 *
 * Backend Pydantic (apps/api/app/schemas/natal.py) — окончательный
 * источник правды для wire-формата. Если расхождение — правим тут.
 */

import { z } from "zod"

// -------------------------------- Meta --------------------------------

export const NatalMetaSchema = z.object({
  name: z.string().min(1),
  birth: z.object({
    date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    time: z.string().optional(),
    timezone: z.string().optional(),
    place: z.string().optional(),
  }),
  mode: z.string().optional(),
  houseSystem: z.string().optional(),
  generatedAt: z.string().optional(),
})

// -------------------------------- Highlights --------------------------------

export const HighlightSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  value: z.string().min(1),
  hint: z.string().optional(),
})

// -------------------------------- Spheres --------------------------------

export const SphereToneSchema = z.enum(["neutral", "strength", "tension"])

export const SphereScoreSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  dominance: z.number().min(0).max(5),
  metrics: z
    .object({
      involvement: z.number().optional(),
      ease: z.number().optional(),
      tension: z.number().optional(),
      visibility: z.number().optional(),
      shadow: z.number().optional(),
    })
    .optional(),
  tone: SphereToneSchema.optional(),
})

// -------------------------------- Planets --------------------------------

export const PlanetScoreSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  sign: z.string().min(1),
  house: z.union([z.number(), z.string()]).optional(),
  composite: z.number().optional(),
  dignity: z.number().optional(),
  bonification: z.number().optional(),
  inSect: z.boolean().optional(),
  dispositor: z.string().optional(),
  note: z.string().optional(),
})

// -------------------------------- Blocks --------------------------------

export const ParagraphBlockSchema = z.object({
  type: z.literal("paragraph"),
  text: z.string().min(1),
})

export const LeadBlockSchema = z.object({
  type: z.literal("lead"),
  text: z.string().min(1),
})

export const HeadingBlockSchema = z.object({
  type: z.literal("heading"),
  level: z.union([z.literal(2), z.literal(3)]),
  text: z.string().min(1),
})

export const ListBlockSchema = z.object({
  type: z.literal("list"),
  style: z.enum(["bullet", "check"]).optional(),
  items: z.array(z.string()).min(1),
})

export const CalloutToneSchema = z.enum(["neutral", "strength", "risk", "insight"])

export const CalloutBlockSchema = z.object({
  type: z.literal("callout"),
  tone: CalloutToneSchema.optional(),
  title: z.string().optional(),
  text: z.string().min(1),
})

export const ProsConsBlockSchema = z.object({
  type: z.literal("pros_cons"),
  prosLabel: z.string().optional(),
  consLabel: z.string().optional(),
  pros: z.array(z.string()).optional(),
  cons: z.array(z.string()).optional(),
})

export const StatGridBlockSchema = z.object({
  type: z.literal("stat_grid"),
  items: z.array(
    z.object({
      label: z.string().min(1),
      value: z.string().min(1),
    })
  ),
})

export const QuoteBlockSchema = z.object({
  type: z.literal("quote"),
  text: z.string().min(1),
  cite: z.string().optional(),
})

export const DividerBlockSchema = z.object({
  type: z.literal("divider"),
})

export const SpheresWidgetBlockSchema = z.object({
  type: z.literal("spheres_widget"),
  limit: z.number().optional(),
})

export const PlanetsWidgetBlockSchema = z.object({
  type: z.literal("planets_widget"),
})

export const BlockSchema = z.discriminatedUnion("type", [
  ParagraphBlockSchema,
  LeadBlockSchema,
  HeadingBlockSchema,
  ListBlockSchema,
  CalloutBlockSchema,
  ProsConsBlockSchema,
  StatGridBlockSchema,
  QuoteBlockSchema,
  DividerBlockSchema,
  SpheresWidgetBlockSchema,
  PlanetsWidgetBlockSchema,
])

// -------------------------------- Sections --------------------------------

export const ReportSectionSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  eyebrow: z.string().optional(),
  summary: z.string().optional(),
  blocks: z.array(BlockSchema),
})

// -------------------------------- Report --------------------------------

export const NatalReportSchema = z.object({
  schemaVersion: z.literal("natal/v1"),
  meta: NatalMetaSchema,
  highlights: z.array(HighlightSchema).optional(),
  spheres: z.array(SphereScoreSchema).optional(),
  planets: z.array(PlanetScoreSchema).optional(),
  sections: z.array(ReportSectionSchema),
})

// -------------------------------- Types --------------------------------

export type NatalMeta = z.infer<typeof NatalMetaSchema>
export type Highlight = z.infer<typeof HighlightSchema>
export type SphereTone = z.infer<typeof SphereToneSchema>
export type SphereScore = z.infer<typeof SphereScoreSchema>
export type PlanetScore = z.infer<typeof PlanetScoreSchema>
export type Block = z.infer<typeof BlockSchema>
export type ReportSection = z.infer<typeof ReportSectionSchema>
export type NatalReport = z.infer<typeof NatalReportSchema>
export type CalloutTone = z.infer<typeof CalloutToneSchema>

// -------------------------------- Preview Zod Schemas --------------------------------

export const NatalPreviewMetaSchema = z.object({
  name: z.string().nullable().optional(),
  birthDate: z.string().min(1),
  birthTime: z.string().nullable().optional(),
  birthCity: z.string().nullable().optional(),
  houseSystem: z.string().nullable().optional(),
  ascSign: z.string().nullable().optional(),
  ascDegree: z.number().nullable().optional(),
  gender: z.enum(["male", "female"]),
})

export const NatalPreviewHighlightSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  value: z.string().min(1),
  description: z.string().nullable().optional(),
})

export const NatalPreviewSphereSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  score: z.number(),
  rank: z.number(),
  description: z.string().min(1),
})

export const NatalPreviewPlanetSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  sign: z.string().nullable().optional(),
  house: z.union([z.number(), z.string()]).nullable().optional(),
  score: z.number().nullable().optional(),
  description: z.string().min(1),
})

export const NatalPreviewChapterSchema = z.object({
  id: z.string().min(1),
  eyebrow: z.string().min(1),
  title: z.string().min(1),
  locked: z.boolean(),
  description: z.string().min(1),
})

export const NatalCalculationStatsSchema = z.object({
  planetsCount: z.number(),
  housesCount: z.number(),
  aspectsCount: z.number(),
  spheresCount: z.number(),
  specialPointsCount: z.number(),
  scoringFactorsCount: z.number(),
  dignityFactorsCount: z.number(),
  totalFactorsCount: z.number(),
  displayLabel: z.string().min(1),
})

export const NatalPreviewReadSchema = z.object({
  meta: NatalPreviewMetaSchema,
  highlights: z.array(NatalPreviewHighlightSchema),
  spheres: z.array(NatalPreviewSphereSchema),
  planets: z.array(NatalPreviewPlanetSchema),
  chapters: z.array(NatalPreviewChapterSchema),
  personalHook: z.string().min(1),
  calculationStats: NatalCalculationStatsSchema,
  salesBullets: z.array(z.string()),
  fullReportAvailable: z.boolean(),
  fullReportPriceKopecks: z.number(),
})

// -------------------------------- Preview Types (backed by Zod) --------------------------------

export type NatalPreviewMeta = z.infer<typeof NatalPreviewMetaSchema>
export type NatalPreviewHighlight = z.infer<typeof NatalPreviewHighlightSchema>
export type NatalPreviewSphere = z.infer<typeof NatalPreviewSphereSchema>
export type NatalPreviewPlanet = z.infer<typeof NatalPreviewPlanetSchema>
export type NatalPreviewChapter = z.infer<typeof NatalPreviewChapterSchema>
export type NatalCalculationStats = z.infer<typeof NatalCalculationStatsSchema>
export type NatalPreviewRead = z.infer<typeof NatalPreviewReadSchema>

// -------------------------------- Validators --------------------------------

/**
 * Валидирует NatalReport и выбрасывает при несоответствии.
 */
export function validateNatalReport(data: unknown): NatalReport {
  return NatalReportSchema.parse(data)
}

// ===========================================================================
// Wave 5: Backend-aligned types (source: apps/api/app/schemas/natal.py)
// ===========================================================================

/**
 * Callout tone values from backend Pydantic.
 * Frontend display mapping:
 *   info → neutral (default)
 *   warning → risk/caution
 *   insight → insight
 *   positive → strength/success
 */
export const BackendCalloutToneSchema = z.enum(["info", "warning", "insight", "positive"])
export type BackendCalloutTone = z.infer<typeof BackendCalloutToneSchema>

/** ProsConsItem — backend sends {title, text}, not plain strings. */
export const ProsConsItemSchema = z.object({
  title: z.string(),
  text: z.string(),
})
export type ProsConsItem = z.infer<typeof ProsConsItemSchema>

// ---- Backend-aligned block schemas ----

export const BackendParagraphBlockSchema = z.object({
  type: z.literal("paragraph"),
  text: z.string().min(1),
})

export const BackendLeadBlockSchema = z.object({
  type: z.literal("lead"),
  text: z.string().min(1),
})

export const BackendHeadingBlockSchema = z.object({
  type: z.literal("heading"),
  text: z.string().min(1),
  level: z.number().default(2),
})

export const BackendListBlockSchema = z.object({
  type: z.literal("list"),
  items: z.array(z.string()).min(1),
  ordered: z.boolean().default(false),
})

export const BackendCalloutBlockSchema = z.object({
  type: z.literal("callout"),
  title: z.string().nullable().optional(),
  text: z.string().min(1),
  tone: BackendCalloutToneSchema.default("info"),
})

export const BackendProsConsBlockSchema = z.object({
  type: z.literal("pros_cons"),
  prosLabel: z.string().default("Сильные стороны"),
  consLabel: z.string().default("Зоны роста"),
  pros: z.array(ProsConsItemSchema).default([]),
  cons: z.array(ProsConsItemSchema).default([]),
})

export const BackendQuoteBlockSchema = z.object({
  type: z.literal("quote"),
  text: z.string().min(1),
  source: z.string().nullable().optional(),
})

export const BackendDividerBlockSchema = z.object({
  type: z.literal("divider"),
})

export const BackendHighlightsBlockSchema = z.object({
  type: z.literal("highlights"),
  items: z.array(z.object({
    id: z.string(),
    title: z.string(),
    text: z.string(),
    tone: z.string().nullable().optional(),
  })),
})

export const BackendBulletsBlockSchema = z.object({
  type: z.literal("bullets"),
  items: z.array(z.string()),
})

export const BackendBlockSchema = z.discriminatedUnion("type", [
  BackendParagraphBlockSchema,
  BackendLeadBlockSchema,
  BackendHeadingBlockSchema,
  BackendListBlockSchema,
  BackendCalloutBlockSchema,
  BackendProsConsBlockSchema,
  BackendQuoteBlockSchema,
  BackendDividerBlockSchema,
  BackendHighlightsBlockSchema,
  BackendBulletsBlockSchema,
])

export type BackendBlock = z.infer<typeof BackendBlockSchema>

// ---- Backend-aligned report types ----

export const NatalReportMetaSchema = z.object({
  userName: z.string().nullable().optional(),
  birthDate: z.string().nullable().optional(),
  birthTime: z.string().nullable().optional(),
  birthPlace: z.string().nullable().optional(),
  houseSystem: z.string().default("Placidus"),
  contextHash: z.string().nullable().optional(),
  promptVersion: z.string().default("1"),
})
export type NatalReportMeta = z.infer<typeof NatalReportMetaSchema>

export const NatalReportSectionReadSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  summary: z.string().nullable().optional(),
  blocks: z.array(BackendBlockSchema),
})
export type NatalReportSectionRead = z.infer<typeof NatalReportSectionReadSchema>

export const NatalReportStatusSchema = z.enum([
  "PENDING",
  "GENERATING",
  "READY",
  "FAILED_RETRYABLE",
  "FAILED_PERMANENT",
])
export type NatalReportStatus = z.infer<typeof NatalReportStatusSchema>

export const NatalReportAccessStateSchema = z.enum([
  "FREE_PREVIEW",
  "UNLOCKED",
  "INTERNAL_TEST",
  "BLOCKED",
])
export type NatalReportAccessState = z.infer<typeof NatalReportAccessStateSchema>

export const NatalReportReadSchema = z.object({
  id: z.string(),
  status: NatalReportStatusSchema,
  accessState: NatalReportAccessStateSchema.default("FREE_PREVIEW"),
  meta: NatalReportMetaSchema,
  sections: z.array(NatalReportSectionReadSchema).default([]),
  errorCode: z.string().nullable().optional(),
  errorMessage: z.string().nullable().optional(),
  createdAt: z.string().nullable().optional(),
  completedAt: z.string().nullable().optional(),
})
export type NatalReportRead = z.infer<typeof NatalReportReadSchema>

export const NatalGenerateResponseSchema = z.object({
  reportId: z.string(),
  status: NatalReportStatusSchema,
  sectionsAvailable: z.boolean().default(false),
  errorCode: z.string().nullable().optional(),
  errorMessage: z.string().nullable().optional(),
})
export type NatalGenerateResponse = z.infer<typeof NatalGenerateResponseSchema>

/**
 * Валидирует NatalReportRead (backend-формат) и выбрасывает при несоответствии.
 */
export function validateNatalReportRead(data: unknown): NatalReportRead {
  return NatalReportReadSchema.parse(data)
}

/**
 * Maps backend callout tone to frontend display class key.
 * Backend sends: info, warning, insight, positive
 * Frontend renders: neutral, risk, insight, strength
 */
export function mapCalloutTone(tone?: BackendCalloutTone | null): "neutral" | "risk" | "insight" | "strength" {
  switch (tone) {
    case "warning": return "risk"
    case "positive": return "strength"
    case "insight": return "insight"
    case "info":
    default: return "neutral"
  }
}
