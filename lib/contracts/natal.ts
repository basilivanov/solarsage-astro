/**
 * Zod-контракт для Natal (натальный отчёт).
 *
 * Единственный источник правды о форме данных натального отчёта.
 * Версионирован: schemaVersion позволяет фронту держать несколько
 * рендереров параллельно.
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

// -------------------------------- Validators --------------------------------

/**
 * Валидирует NatalReport и выбрасывает при несоответствии.
 */
export function validateNatalReport(data: unknown): NatalReport {
  return NatalReportSchema.parse(data)
}
