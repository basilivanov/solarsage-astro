
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_TODAY
// ROLE: UI — today
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI today — component
// owns:
//   - lib/contracts/today.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-CONTRACTS-TODAY
// wave: W-2.7
// purpose: Today contracts (migrated from legacy)

/**
 * Zod-контракт для Today (данные дня).
 *
 * Единственный источник правды о форме данных экрана дня.
 */

import { z } from "zod"

export const DayStatusSchema = z.enum(["supportive", "steady", "tense"]);

export type DayStatus = z.infer<typeof DayStatusSchema>;

export const AdaptedTopFlagSchema = z.object({
  /** Имя иконки для отображения */
  iconName: z.string().min(1),
  /** Короткий заголовок флага */
  title: z.string().min(1),
  /** Краткое описание-подпись */
  summary: z.string().min(1),
});

export type AdaptedTopFlag = z.infer<typeof AdaptedTopFlagSchema>;

export const IconNameSchema = z.enum([
  "moon",
  "orbit",
  "briefcase",
  "compass",
  "hourglass",
  "target",
  "layers",
  "trending-up",
  "leaf",
  "grid",
  "telescope",
  "list-checks",
  "zap",
  "sparkle",
  "check",
  "building",
])

export const TodayNoteHintSchema = z.object({
  meaning: z.string().min(1),
  whyImportant: z.string().min(1),
  howForMe: z.string().min(1),
})

export const TodayNoteSchema = z.object({
  id: z.string().min(1),
  iconName: z.string().min(1), // Более мягкая проверка — fallback на Compass в UI
  title: z.string().min(1),
  description: z.string().min(1),
  hint: TodayNoteHintSchema,
})

export const TodayReadingSchema = z.object({
  /** Абзацы разбора по порядку. Первый получает dropcap-стиль в UI. */
  paragraphs: z.array(z.string().min(1)).min(1),
})

export const DayChartHouseSchema = z.object({
  number: z.number().int(),
  cuspLongitude: z.number(),
  sign: z.string().nullable().optional(),
})

export const DayChartTransitPlanetSchema = z.object({
  name: z.string().min(1),
  longitude: z.number(),
  sign: z.string().nullable().optional(),
  retrograde: z.boolean().nullable().optional(),
  speed: z.number().nullable().optional(),
  motion: z.enum(["direct", "retrograde", "stationary"]).nullable().optional(),
  house: z.number().int().nullable().optional(),
  interpretation: z.string().nullable().optional(),
})

export const DayChartAspectSchema = z.object({
  planet: z.string().min(1),
  targetPlanet: z.string().min(1),
  aspectType: z.string().min(1),
  orb: z.number().nullable().optional(),
  strength: z.number().nullable().optional(),
})

export const DayChartSchema = z.object({
  source: z.literal("solarsage"),
  houses: z.array(DayChartHouseSchema),
  transitPlanets: z.array(DayChartTransitPlanetSchema),
  aspects: z.array(DayChartAspectSchema),
})

export const PlanetInfluenceSchema = z.object({
  name: z.string().min(1),
  score: z.number(),
  rank: z.number().int(),
})

export const SphereScoreSchema = z.object({
  key: z.string().min(1),
  score: z.number(),
  rank: z.number().int(),
})

export const TodayWhySectionSchema = z.object({
  id: z.string().min(1),
  iconName: z.string().min(1),
  title: z.string().min(1),
  paragraphs: z.array(z.string().min(1)),
  bullets: z.array(z.string().min(1)).optional(),
}).refine(
  (section) => section.paragraphs.length > 0 || (section.bullets?.length ?? 0) > 0,
  { message: "why section must contain paragraphs or bullets" },
)

export const ConcreteAdviceEvidenceSchema = z.object({
  kind: z.enum(["sphere_score", "aspect", "planet_in_house", "day_status", "lunar", "important_today", "activation", "score_contribution"]),
  title: z.string().min(1),
  weight: z.number().nullable().optional(),
  planet: z.string().nullable().optional(),
  targetPlanet: z.string().nullable().optional(),
  aspectType: z.string().nullable().optional(),
  orb: z.number().nullable().optional(),
  strength: z.number().nullable().optional(),
  sphereKey: z.string().nullable().optional(),
  house: z.number().int().nullable().optional(),
  sign: z.string().nullable().optional(),
  activationId: z.string().nullable().optional(),
  technique: z.string().nullable().optional(),
  techniqueFamily: z.string().nullable().optional(),
  sourceFrame: z.string().nullable().optional(),
  targetFrame: z.string().nullable().optional(),
  contributionSourceId: z.string().nullable().optional(),
})

export const ConcreteAdviceRowSchema = z.object({
  key: z.enum([
    "work", "money", "documents", "relationships", "sport", "communication",
    "health", "decisions", "travel", "creativity", "study", "shopping"
  ]),
  label: z.string().min(1),
  iconName: z.string().min(1),
  rank: z.number().int(),
  verdict: z.enum(["good", "caution", "avoid", "neutral"]),
  confidence: z.enum(["high", "medium", "low"]),
  text: z.string().min(1),
  evidence: z.array(ConcreteAdviceEvidenceSchema),
})

export const ConcreteAdviceCountsSchema = z.object({
  good: z.number().int(),
  caution: z.number().int(),
  avoid: z.number().int(),
  neutral: z.number().int(),
})

export const ConcreteAdviceBlockSchema = z.object({
  rows: z.array(ConcreteAdviceRowSchema),
  counts: ConcreteAdviceCountsSchema,
})

export const DaySummaryFactSchema = z.object({
  kind: z.enum(["top_planet", "lunar_phase", "void_moon", "top_flag"]),
  iconName: z.string().min(1),
  title: z.string().min(1),
  summary: z.string().nullable().optional(),
})

export const DaySummaryBlockSchema = z.object({
  statusLabel: z.string().min(1),
  statusLine: z.string().min(1),
  facts: z.array(DaySummaryFactSchema),
})

export const ActivationTargetTypeSchema = z.enum(["planet", "house", "lot", "angle", "sphere"])
export const ActivationPolaritySchema = z.enum(["supportive", "tense", "mixed", "neutral"])
export const ActivationPhaseSchema = z.enum(["applying", "exact", "separating", "background", "period"])

export const ActivationEvidenceSchema = z.object({
  id: z.string().min(1),
  technique: z.string().min(1),
  techniqueFamily: z.string().min(1),
  targetType: ActivationTargetTypeSchema,
  targetKey: z.string().min(1),
  kind: z.string().min(1),
  active: z.boolean().default(true),
  sourcePlanet: z.string().nullable().optional(),
  sourceFrame: z.string().nullable().optional(),
  targetPlanet: z.string().nullable().optional(),
  targetFrame: z.string().nullable().optional(),
  aspect: z.string().nullable().optional(),
  orb: z.number().nullable().optional(),
  applying: z.boolean().nullable().optional(),
  activeFrom: z.string().nullable().optional(),
  exactAt: z.string().nullable().optional(),
  activeUntil: z.string().nullable().optional(),
  phase: ActivationPhaseSchema.default("background"),
  house: z.number().int().nullable().optional(),
  lot: z.string().nullable().optional(),
  angle: z.string().nullable().optional(),
  strength: z.number().min(0).max(1),
  polarity: ActivationPolaritySchema.default("neutral"),
  weightHint: z.number().nullable().optional(),
  evidence: z.string().min(1),
  debug: z.record(z.any()).default({}),
})

export const SphereContributionSchema = z.object({
  sphere: z.string().min(1),
  source: z.enum(["base_signal", "activation", "convergence", "cap"]),
  sourceId: z.string().min(1),
  amount: z.number(),
  before: z.number().nullable().optional(),
  after: z.number().nullable().optional(),
  evidence: z.string().min(1),
})

export const SphereScoreV2Schema = z.object({
  key: z.string().min(1),
  title: z.string().min(1),
  baseScore: z.number(),
  activationScore: z.number(),
  convergenceBonus: z.number(),
  rawScore: z.number(),
  finalScore: z.number(),
  normalizedScore: z.number().nullable().optional(),
  dominanceCapped: z.boolean(),
  contributions: z.array(SphereContributionSchema),
})

export const TodayV2ActivatedTargetSchema = z.object({
  targetType: z.enum(["planet", "house", "lot", "angle", "sphere"]),
  targetKey: z.string().min(1),
  label: z.string().min(1),
  familyCount: z.number().int(),
  techniques: z.array(z.string()),
  spheres: z.array(z.string()),
  activationIds: z.array(z.string()),
})

export const TodayV2ActivationSummarySchema = z.object({
  headline: z.string().min(1),
  topActivatedTargets: z.array(TodayV2ActivatedTargetSchema),
})

export const TodayV2WhyTodayItemSchema = z.object({
  id: z.string().min(1),
  title: z.string().min(1),
  body: z.string().min(1),
  activationIds: z.array(z.string()),
  techniques: z.array(z.string()),
})

export const TodayV2AuditSchema = z.object({
  traceId: z.string().nullable().optional(),
  available: z.boolean().default(false),
  payloadVersion: z.string(),
  calculationVersion: z.union([z.string(), z.number()]),
  scoringVersion: z.union([z.string(), z.number()]),
  activationLayerVersion: z.union([z.string(), z.number()]).nullable().optional(),
  canonVersions: z.record(z.string()),
  v1V2Diff: z.record(z.any()).nullable().optional(),
})

export const TodayV2BlockSchema = z.object({
  activationSummary: TodayV2ActivationSummarySchema,
  activationEvidence: z.array(ActivationEvidenceSchema),
  scoreBreakdown: z.record(SphereScoreV2Schema),
  whyToday: z.array(TodayV2WhyTodayItemSchema),
  audit: TodayV2AuditSchema,
})

export const TodayPayloadSchema = z.object({
  /** ISO yyyy-mm-dd — для кэша, deeplink'ов, инвалидации SWR. */
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  /** Заголовок дня от LLM */
  headline: z.string(),
  /** Общий статус дня */
  dayStatus: DayStatusSchema,
  daySummary: DaySummaryBlockSchema,
  concreteAdvice: ConcreteAdviceBlockSchema,
  /** Флаги / карточки дня (топ-сигналы) */
  topFlags: z.array(AdaptedTopFlagSchema),
  notes: z.array(TodayNoteSchema),
  reading: TodayReadingSchema,
  why: z.array(TodayWhySectionSchema),
  /** Короткий «ключ дня», закрывающий блок «Почему так у меня». */
  keyInsight: z.string().min(1),
  dayChart: DayChartSchema.nullable().default(null),
  planetInfluences: z.array(PlanetInfluenceSchema).default([]),
  sphereScores: z.array(SphereScoreSchema).default([]),
  /** W6: optional V2 block */
  v2: TodayV2BlockSchema.nullable().optional(),
})

export type IconName = z.infer<typeof IconNameSchema>
export type TodayNote = z.infer<typeof TodayNoteSchema>
export type TodayReading = z.infer<typeof TodayReadingSchema>
export type DayChart = z.infer<typeof DayChartSchema>
export type PlanetInfluence = z.infer<typeof PlanetInfluenceSchema>
export type SphereScore = z.infer<typeof SphereScoreSchema>
export type TodayWhySection = z.infer<typeof TodayWhySectionSchema>
export type ConcreteAdviceBlock = z.infer<typeof ConcreteAdviceBlockSchema>
export type ConcreteAdviceRow = z.infer<typeof ConcreteAdviceRowSchema>
export type DaySummaryBlock = z.infer<typeof DaySummaryBlockSchema>
export type AdaptedTodayPayload = z.infer<typeof TodayPayloadSchema>
export type TodayV2Block = z.infer<typeof TodayV2BlockSchema>
export type TodayV2ActivatedTarget = z.infer<typeof TodayV2ActivatedTargetSchema>
export type TodayV2ActivationSummary = z.infer<typeof TodayV2ActivationSummarySchema>
export type TodayV2WhyTodayItem = z.infer<typeof TodayV2WhyTodayItemSchema>
export type TodayV2Audit = z.infer<typeof TodayV2AuditSchema>
export type ActivationEvidence = z.infer<typeof ActivationEvidenceSchema>
export type SphereScoreV2 = z.infer<typeof SphereScoreV2Schema>

export function validateAdaptedTodayPayload(data: unknown): AdaptedTodayPayload {
  return TodayPayloadSchema.parse(data)
}
