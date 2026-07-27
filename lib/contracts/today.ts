
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_TODAY — UI-adapted today screen contracts.
// ROLE: Defines Zod schemas and TypeScript types for today screen UI representation.
// DEPENDENCIES: packages/contracts, packages/contracts/runtime
// ############################################################################

// START_MODULE_CONTRACT: M-CONTRACTS-TODAY
// purpose: Today screen UI-adapted contract definitions.
// owns:
//   - lib/contracts/today.ts
// inputs: none.
// outputs:
//   - UI Zod schemas: DayStatusSchema, AdaptedTopFlagSchema, TodayNoteSchema, TodayWhySectionSchema, AdaptedTodayPayload, TodayWireIdentitySchema
//   - UI TypeScript types: AdaptedTodayPayload, TodayNote, TodayReading, TodayWhySection, TodayWireIdentity
//   - V2 wire schemas/values are imported from generated runtime barrel
// dependencies: packages/contracts, packages/contracts/runtime.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - No manual raw V2 wire schema object declarations.
//   - TodayWireIdentitySchema derived from generated Today meta .pick(), never manually redeclared.
//   - wireIdentity field optional only for legacy adapted artifacts; real adapter always populates.
//   - Missing identity remains unknown/fail-closed.
// failure_policy: compile error on missing definitions.
// END_MODULE_CONTRACT: M-CONTRACTS-TODAY

// START_MODULE_MAP: M-CONTRACTS-TODAY
// public_entrypoints:
//   - AdaptedTodayPayload
//   - TodayPayloadSchema
//   - TodayV2BlockSchema
//   - TodayWireIdentitySchema
//   - TodayWireIdentity
//   - validateAdaptedTodayPayload
// semantic_blocks:
//   - UI_SCHEMAS: Zod schemas for adapted UI blocks.
//   - WIRE_IDENTITY: generated pick of meta identity for consumer routing.
//   - GENERATED_V2_WIRE_SCHEMA_ALIAS: aliases generated V2 wire validation without redeclaring its shape.
// END_MODULE_MAP: M-CONTRACTS-TODAY

import { z } from "zod"
import type {
  TodayV2Block as TodayV2BlockWire,
  TodayV2ActivatedTarget as TodayV2ActivatedTargetWire,
  TodayV2ActivationSummary as TodayV2ActivationSummaryWire,
  TodayV2WhyTodayItem as TodayV2WhyTodayItemWire,
  TodayV2Audit as TodayV2AuditWire,
  TodayV2Provenance as TodayV2ProvenanceWire,
  TodayV2GroundedItem as TodayV2GroundedItemWire,
  TodayV2HorizonTiming as TodayV2HorizonTimingWire,
  TodayV2TechniqueExplanation as TodayV2TechniqueExplanationWire,
  TodayV2Manifestation as TodayV2ManifestationWire,
  TodayV2HorizonActions as TodayV2HorizonActionsWire,
  TodayV2Horizon as TodayV2HorizonWire,
  TodayV2HorizonIntro as TodayV2HorizonIntroWire,
  TodayV2HorizonsBlock as TodayV2HorizonsBlockWire,
  ActivationEvidence as ActivationEvidenceWire,
  SphereScoreV2 as SphereScoreV2Wire,
} from "@/packages/contracts"
import {
  TodayPayloadWireSchema,
  TodayV2BlockWireSchema,
  TodayV2HorizonsBlockWireSchema,
  TodayV2HorizonWireSchema,
  TodayV2HorizonTimingWireSchema,
  TodayV2ProvenanceWireSchema,
} from "@/packages/contracts/runtime"

// START_BLOCK: WIRE_IDENTITY
// Generated pick of the three meta identity fields used for consumer routing.
export const TodayWireIdentitySchema = TodayPayloadWireSchema.shape.meta.pick({
  payloadVersion: true,
  frontendPayloadVersion: true,
  contentVersion: true,
})
export type TodayWireIdentity = z.infer<typeof TodayWireIdentitySchema>
// END_BLOCK: WIRE_IDENTITY

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

// START_BLOCK: GENERATED_V2_WIRE_SCHEMA_ALIAS
// Today V2 wire validation is generated from Pydantic/OpenAPI and re-exported
// through the stable runtime barrel; this UI module does not redeclare its shape.
export const TodayV2BlockSchema = TodayV2BlockWireSchema
export const TodayV2HorizonsBlockSchema = TodayV2HorizonsBlockWireSchema
export const TodayV2HorizonSchema = TodayV2HorizonWireSchema
export const TodayV2HorizonTimingSchema = TodayV2HorizonTimingWireSchema
export const TodayV2ProvenanceSchema = TodayV2ProvenanceWireSchema
// END_BLOCK: GENERATED_V2_WIRE_SCHEMA_ALIAS

export const RelativeStatusBaselineSchema = z.object({
  days: z.number().int(),
  supportMean: z.number(),
  supportStd: z.number(),
  tensionMean: z.number(),
  tensionStd: z.number(),
})

export const RelativeDayStatusSchema = z.object({
  baseline: RelativeStatusBaselineSchema,
  label: z.string(),
  mode: z.enum(["absolute", "relative"]),
  status: z.enum(["usual", "softer", "tenser", "hard", "strong"]),
  supportBand: z.array(z.number()).optional(),
  supportMarker: z.number().optional().default(0.5),
  tensionBand: z.array(z.number()).optional(),
  tensionMarker: z.number().optional().default(0.5),
  zSupport: z.number(),
  zTension: z.number(),
})

export const TodayPayloadSchema = z.object({
  /** Wire identity for consumer routing. Real adapter always sets it. */
  wireIdentity: TodayWireIdentitySchema.optional(),
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
  /** W-DAY: relative day status vs personal baseline (optional; absent on old payloads). */
  relativeStatus: RelativeDayStatusSchema.nullable().optional(),
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
export type TodayV2Block = TodayV2BlockWire
export type TodayV2ActivatedTarget = TodayV2ActivatedTargetWire
export type TodayV2ActivationSummary = TodayV2ActivationSummaryWire
export type TodayV2WhyTodayItem = TodayV2WhyTodayItemWire
export type TodayV2Audit = TodayV2AuditWire
export type TodayV2Provenance = TodayV2ProvenanceWire
export type TodayV2GroundedItem = TodayV2GroundedItemWire
export type TodayV2HorizonTiming = TodayV2HorizonTimingWire
export type TodayV2TechniqueExplanation = TodayV2TechniqueExplanationWire
export type TodayV2Manifestation = TodayV2ManifestationWire
export type TodayV2HorizonActions = TodayV2HorizonActionsWire
export type TodayV2Horizon = TodayV2HorizonWire
export type TodayV2HorizonIntro = TodayV2HorizonIntroWire
export type TodayV2HorizonsBlock = TodayV2HorizonsBlockWire
export type ActivationEvidence = ActivationEvidenceWire
export type SphereScoreV2 = SphereScoreV2Wire

export function validateAdaptedTodayPayload(data: unknown): AdaptedTodayPayload {
  return TodayPayloadSchema.parse(data)
}
