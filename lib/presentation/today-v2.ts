// ############################################################################
// AI_HEADER: MODULE_LIB_PRESENTATION_TODAY_V2
// ROLE: Presentation-only localization/formatting for Today V2 structured fields.
//       No scoring, convergence, or astrology calculation.
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-PRESENTATION-TODAY-V2
// purpose: Localize, rank, and explain backend-owned V2 activation evidence for UI.
// owns:
//   - lib/presentation/today-v2.ts
// inputs: structured V2 evidence / technique / sphere / phase fields
// outputs: Russian labels, human evidence titles, three-horizon models, and technical education copy
// dependencies: none (pure presentation)
// side_effects: none
// emitted_logs: none
// invariants:
//   - Never recalculates astrology, convergence, or backend scores; ranks only existing backend evidence for presentation
//   - Never exposes activation IDs, debug JSON, or raw strength in primary UI
//   - Planet targets use dative case after «к вашему натальному»
//   - Strips Transit_/Natal_ prefixes before planet mapping
// failure_policy: safe Russian fallbacks; never throws
// END_MODULE_CONTRACT: M-LIB-PRESENTATION-TODAY-V2

// START_MODULE_MAP: M-LIB-PRESENTATION-TODAY-V2
// public_entrypoints:
//   - getTechniqueLabel
//   - normalizePlanetKey
//   - getPlanetLabelRu
//   - getPlanetLabelRuDative
//   - getAspectLabelRu
//   - getPhaseLabelRu
//   - getSphereLabelConcise
//   - formatActivationEvidenceTitle
//   - formatConcreteAdviceEvidenceTitle
//   - dedupeTechniquesPreserveOrder
//   - selectPrimaryEvidence
//   - getHumanSphereLabel
//   - containsBannedAstrologyVocabulary
//   - getSafeWhyTodayItem
//   - getVerdictManifestationCopy
//   - orderActivationEvidence
//   - selectWhyTimeHorizons
//   - getEvidenceDurationLabel
//   - getEvidenceStageLabel
//   - getTechnicalEvidenceExplanation
//   - getEvidenceTimingPreview
// semantic_blocks:
//   - LABELS: planet/aspect/phase/technique/sphere maps
//   - FORMATTERS: human evidence titles
//   - HORIZON_SELECTION: related evidence classification and deterministic three-horizon ranking
//   - TECHNICAL_EDUCATION: duration, stage, and technique/planet explanations
//   - PREVIEW_TIMING_BRIDGE: temporary compatibility for timing fields
// owned_tests:
//   - __tests__/lib/presentation/today-v2.test.ts
// END_MODULE_MAP: M-LIB-PRESENTATION-TODAY-V2

import type {
  ActivationEvidence,
  TodayV2Block,
  TodayV2ActivatedTarget,
  TodayV2WhyTodayItem,
} from "@/packages/contracts"
import type {
  ConcreteAdviceRow,
} from "@/lib/contracts/today"

// START_BLOCK: LABELS
export const TECHNIQUE_LABELS: Record<string, string> = {
  transit_to_natal: "Транзит",
  transit_to_angle: "Транзит",
  transit_to_lot: "Транзит",
  transit_planet_in_house: "Транзит",
  annual_profection: "Профекция",
  monthly_profection: "Профекция",
  firdar_major: "Фирдар",
  firdar_minor: "Фирдар",
  solar_return: "Возвращение",
  lunar_return: "Возвращение",
  secondary_progression: "Прогрессия",
  solar_arc: "Солнечная дуга",
  eclipse_window: "Затмение",
}

/** Nominative planet labels after prefix strip. */
const PLANET_LABELS_NOMINATIVE: Record<string, string> = {
  SUN: "Солнце",
  MOON: "Луна",
  MERCURY: "Меркурий",
  VENUS: "Венера",
  MARS: "Марс",
  JUPITER: "Юпитер",
  SATURN: "Сатурн",
  URANUS: "Уран",
  NEPTUNE: "Нептун",
  PLUTO: "Плутон",
}

/** Dative planet labels for «к вашему натальному …». */
const PLANET_LABELS_DATIVE: Record<string, string> = {
  SUN: "Солнцу",
  MOON: "Луне",
  MERCURY: "Меркурию",
  VENUS: "Венере",
  MARS: "Марсу",
  JUPITER: "Юпитеру",
  SATURN: "Сатурну",
  URANUS: "Урану",
  NEPTUNE: "Нептуну",
  PLUTO: "Плутону",
}

const ASPECT_LABELS: Record<string, string> = {
  conjunction: "соединение",
  sextile: "секстиль",
  square: "квадрат",
  trine: "тригон",
  opposition: "оппозиция",
}

const PHASE_LABELS: Record<string, string> = {
  applying: "сходящийся",
  exact: "точный",
  separating: "расходящийся",
  background: "долгий период",
  period: "долгий период",
}

/** Concise product sphere labels for the personal card (≤3 shown). */
const SPHERE_CONCISE: Record<string, string> = {
  thinking_speech_learning: "Мысли и речь",
  work_status_achievement: "Работа и статус",
  relationships_partnership: "Отношения",
  money_security_resources: "Деньги и ресурсы",
  body_energy_health: "Тело и энергия",
  home_family_roots: "Дом и семья",
  inner_background_unconscious: "Внутренний фон",
  crisis_transformation_control: "Перемены и контроль",
  meaning_expansion_vector: "Смысл и вектор",
}

const TECHNIQUE_FALLBACKS: Array<{ match: RegExp; text: string }> = [
  { match: /profection/i, text: "Профекция усиливает эту тему в текущем жизненном цикле" },
  { match: /firdar/i, text: "Фирдар подтверждает долгосрочный фокус темы" },
  { match: /return/i, text: "Карта возвращения повторно выделяет эту тему" },
  { match: /progression|solar_arc/i, text: "Медленный личный цикл подтверждает изменение темы" },
  { match: /eclipse/i, text: "Коридор затмения усиливает чувствительность этой точки" },
]

const RAW_ENGLISH_RE =
  /\b(transit|natal|orb|source_frame|target_frame|convergence|bonus|dominance|cap|техника:|семейство:)\b/i
// END_BLOCK: LABELS

// START_BLOCK: FORMATTERS
/**
 * Strip Transit_/Natal_ and spaced Transit/Natal prefixes before planet mapping.
 * V1 evidence planet fields may contain Transit_Mars / Natal Pluto.
 */
export function normalizePlanetKey(name: string | null | undefined): string | null {
  if (name == null) return null
  let key = String(name).trim()
  if (!key) return null
  key = key.replace(/^(Transit_|Natal_|transit_|natal_)/i, "")
  key = key.replace(/^(Transit|Natal)\s+/i, "")
  key = key.trim()
  return key || null
}

function planetCanonKey(name: string | null | undefined): string | null {
  const stripped = normalizePlanetKey(name)
  if (!stripped) return null
  return stripped.toUpperCase()
}

export function getTechniqueLabel(technique: string): string {
  if (!technique) return "Дополнительный цикл"
  return TECHNIQUE_LABELS[technique] || "Дополнительный цикл"
}

export function getPlanetLabelRu(name: string | null | undefined): string {
  const canon = planetCanonKey(name)
  if (!canon) return "точка карты"
  return PLANET_LABELS_NOMINATIVE[canon] || normalizePlanetKey(name) || "точка карты"
}

/** Dative form for use after «к вашему натальному». */
export function getPlanetLabelRuDative(name: string | null | undefined): string {
  const canon = planetCanonKey(name)
  if (!canon) return "точке карты"
  return PLANET_LABELS_DATIVE[canon] || getPlanetLabelRu(name)
}

export function getAspectLabelRu(aspect: string | null | undefined): string {
  if (!aspect) return "аспект"
  const key = String(aspect).trim().toLowerCase()
  return ASPECT_LABELS[key] || key
}

export function getPhaseLabelRu(phase: string | null | undefined): string | null {
  if (!phase) return null
  return PHASE_LABELS[phase] || null
}

export function getSphereLabelConcise(key: string): string {
  return SPHERE_CONCISE[key] || "Сфера дня"
}

export function formatOrb(orb: number | null | undefined): string | null {
  if (orb === null || orb === undefined || Number.isNaN(Number(orb))) return null
  return `${Number(orb).toFixed(2)}°`
}

function looksLikeRawEnglish(text: string): boolean {
  if (!text) return true
  if (RAW_ENGLISH_RE.test(text)) return true
  // Latin-heavy technical dump
  const letters = text.replace(/[^A-Za-zА-Яа-яЁё]/g, "")
  if (letters.length === 0) return false
  const latin = (text.match(/[A-Za-z]/g) || []).length
  return latin / letters.length > 0.55
}

/**
 * Human title for activation evidence. Prefer structured fields; never dump raw English evidence as primary.
 * Example: Луна — оппозиция к вашему натальному Плутону
 */
export function formatActivationEvidenceTitle(ev: {
  technique?: string | null
  kind?: string | null
  sourcePlanet?: string | null
  targetPlanet?: string | null
  targetKey?: string | null
  aspect?: string | null
  phase?: string | null
  evidence?: string | null
}): string {
  const src = getPlanetLabelRu(ev.sourcePlanet)
  const tgtPlanet =
    ev.targetPlanet || (ev.targetKey && !/^\d+$/.test(ev.targetKey) ? ev.targetKey : null)
  const tgtDative = getPlanetLabelRuDative(tgtPlanet)
  const aspect = getAspectLabelRu(ev.aspect)

  if (ev.aspect && (ev.sourcePlanet || tgtPlanet)) {
    return `${src} — ${aspect} к вашему натальному ${tgtDative}`
  }

  for (const fb of TECHNIQUE_FALLBACKS) {
    if (ev.technique && fb.match.test(ev.technique)) return fb.text
  }

  const raw = (ev.evidence || "").trim()
  if (raw && !looksLikeRawEnglish(raw)) {
    return raw
  }
  return "Персональный фактор дня"
}

/**
 * Human title for concrete-advice evidence rows.
 * Handles score_contribution kinds without leaking English convergence/cap copy.
 */
export function formatConcreteAdviceEvidenceTitle(ev: {
  title?: string | null
  kind?: string | null
  technique?: string | null
  planet?: string | null
  targetPlanet?: string | null
  aspectType?: string | null
  orb?: number | null
  contributionSourceId?: string | null
  activationId?: string | null
}): string {
  const kind = (ev.kind || "").toLowerCase()
  const contribId = String(ev.contributionSourceId || "").toLowerCase()
  const titleLower = String(ev.title || "").toLowerCase()

  // score_contribution / contribution-like sources
  if (
    kind === "score_contribution" ||
    contribId.startsWith("convergence:") ||
    contribId.startsWith("cap:") ||
    titleLower.includes("convergence")
  ) {
    if (contribId.startsWith("convergence:") || titleLower.includes("convergence")) {
      return "Несколько независимых циклов усиливают эту сферу"
    }
    if (contribId.startsWith("cap:") || /\bcap\b|dominance/i.test(titleLower)) {
      return "Итоговый акцент сферы ограничен, чтобы один фактор не доминировал"
    }
    // activation contribution without structured planet/aspect
    if (ev.aspectType && (ev.planet || ev.targetPlanet)) {
      // fall through to structured formatting below
    } else {
      return "Персональный фактор усиливает эту сферу"
    }
  }

  if (ev.aspectType && (ev.planet || ev.targetPlanet)) {
    const src = getPlanetLabelRu(ev.planet)
    const tgtDative = getPlanetLabelRuDative(ev.targetPlanet)
    const aspect = getAspectLabelRu(ev.aspectType)
    return `${src} — ${aspect} к вашему натальному ${tgtDative}`
  }

  for (const fb of TECHNIQUE_FALLBACKS) {
    if (ev.technique && fb.match.test(ev.technique)) return fb.text
  }

  const title = (ev.title || "").trim()
  if (title && !looksLikeRawEnglish(title)) {
    return title
  }

  if (ev.technique) {
    // Prefer technique-family human fallbacks already handled; otherwise generic
    for (const fb of TECHNIQUE_FALLBACKS) {
      if (fb.match.test(ev.technique)) return fb.text
    }
    return "Персональный фактор усиливает эту сферу"
  }

  return "Персональный фактор"
}

export function dedupeTechniquesPreserveOrder(techniques: string[]): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const t of techniques) {
    if (!t || seen.has(t)) continue
    seen.add(t)
    out.push(t)
  }
  return out
}

/**
 * Presentation-only evidence selection:
 * follow activationIds from first top target in backend order; at most 3;
 * fallback to first three active evidence items.
 */
export function selectPrimaryEvidence(
  evidence: ActivationEvidence[],
  primaryTarget: TodayV2ActivatedTarget | null | undefined,
  max = 3,
): ActivationEvidence[] {
  const byId = new Map(evidence.map((e) => [e.id, e]))
  const ordered: ActivationEvidence[] = []
  if (primaryTarget?.activationIds?.length) {
    for (const id of primaryTarget.activationIds) {
      const hit = byId.get(id)
      if (hit) ordered.push(hit)
      if (ordered.length >= max) break
    }
  }
  if (ordered.length > 0) return ordered.slice(0, max)
  return evidence.filter((e) => e.active !== false).slice(0, max)
}
// END_BLOCK: FORMATTERS

// START_BLOCK: HUMAN_FIRST_PRESENTATION
const HUMAN_SPHERE_LABELS: Record<string, string> = {
  work: "Работа и статус",
  money: "Деньги и решения",
  documents: "Документы и сроки",
  relationships: "Отношения",
  sport: "Тело и энергия",
  communication: "Общение",
  health: "Внутреннее состояние",
  decisions: "Решения и перемены",
  travel: "Поездки",
  creativity: "Творчество",
  study: "Учёба",
  shopping: "Покупки",
}

const HUMAN_BANNED_ASTROLOGY_RE =
  /(транзит|профекци|фирдар|орб|натальн|аспект|сходимост|техник|технич|convergence|source[_\s-]?frame|target[_\s-]?frame)/iu

const LONG_CYCLE_TECHNIQUES = new Set([
  "annual_profection",
  "monthly_profection",
  "firdar_major",
  "firdar_minor",
])

const VERDICT_MANIFESTATION_COPY: Record<string, string> = {
  good: "В этой сфере сегодня больше поддержки.",
  caution: "В этой сфере сегодня особенно важны точность и отсутствие спешки.",
  avoid: "В этой сфере сегодня выше риск поспешного шага.",
  neutral: "В этой сфере сегодня спокойный, нейтральный фон.",
}

// START_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getHumanSphereLabel
// purpose: Return the approved human-first sphere label for a backend row.
// inputs: row — backend-owned concrete advice row.
// returns: Human label mapped by key, or backend label for unknown keys.
// side_effects: none.
// emitted_logs: none.
// error_behavior: never throws; falls back to a safe generic label.
// END_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getHumanSphereLabel
export function getHumanSphereLabel(row: Pick<ConcreteAdviceRow, "label"> & { key: string }): string {
  return HUMAN_SPHERE_LABELS[row.key] || row.label || "Сфера дня"
}

// START_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.containsBannedAstrologyVocabulary
// purpose: Detect technical astrology vocabulary prohibited in human-first surfaces.
// inputs: text — visible candidate copy.
// returns: true when technical vocabulary is present.
// side_effects: none.
// emitted_logs: none.
// error_behavior: nullish text is safe and returns false.
// END_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.containsBannedAstrologyVocabulary
export function containsBannedAstrologyVocabulary(text: string | null | undefined): boolean {
  return HUMAN_BANNED_ASTROLOGY_RE.test(text || "")
}

// START_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getSafeWhyTodayItem
// purpose: Preserve safe backend why copy or deterministically replace technical wording.
// inputs: item — backend-owned whyToday item.
// returns: Human-safe title/body pair.
// side_effects: none.
// emitted_logs: none.
// error_behavior: never exposes a technical title/body when the source is unsuitable.
// END_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getSafeWhyTodayItem
export function getSafeWhyTodayItem(item: TodayV2WhyTodayItem): { title: string; body: string } {
  const title = containsBannedAstrologyVocabulary(item.title) ? "Личный фактор дня" : item.title
  if (!containsBannedAstrologyVocabulary(item.body)) {
    return { title, body: item.body }
  }

  if (item.techniques.some((technique) => LONG_CYCLE_TECHNIQUES.has(technique))) {
    return {
      title,
      body: "Тема поддерживается более длинным личным циклом, поэтому ощущается заметнее обычного.",
    }
  }
  if (item.techniques.some((technique) => technique.startsWith("transit_"))) {
    return { title, body: "Сегодняшний личный фактор делает эту тему заметнее обычного." }
  }
  return { title, body: "Эта тема подтверждается персональными факторами дня." }
}

// START_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getVerdictManifestationCopy
// purpose: Convert a backend verdict enum into approved deterministic human copy.
// inputs: verdict — concrete advice verdict enum.
// returns: Fixed presentation text for that enum.
// side_effects: none.
// emitted_logs: none.
// error_behavior: unknown values use the neutral text.
// END_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getVerdictManifestationCopy
export function getVerdictManifestationCopy(verdict: string): string {
  return VERDICT_MANIFESTATION_COPY[verdict] || VERDICT_MANIFESTATION_COPY.neutral
}

// START_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.orderActivationEvidence
// purpose: Order active evidence by the backend-owned primary activation ID sequence.
// inputs: evidence — V2 activation evidence; primaryTarget — primary backend target.
// returns: Active evidence in primary order, or active backend order as fallback.
// side_effects: none.
// emitted_logs: none.
// error_behavior: never throws; absent references are skipped.
// END_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.orderActivationEvidence
export function orderActivationEvidence(
  evidence: ActivationEvidence[],
  primaryTarget: TodayV2ActivatedTarget | null | undefined,
): ActivationEvidence[] {
  if (!primaryTarget?.activationIds.length) return evidence.filter((item) => item && item.active !== false)
  const byId = new Map(evidence.map((item) => [item.id, item]))
  const selected = primaryTarget.activationIds
    .map((id) => byId.get(id))
    .filter((item): item is ActivationEvidence => Boolean(item && item.active !== false))
  return selected.length > 0 ? selected : evidence.filter((item) => item && item.active !== false)
}

export type WhyTimeHorizonId = "long" | "medium" | "fast"

export type WhyTimeHorizon = {
  id: WhyTimeHorizonId
  evidence: ActivationEvidence[]
  whyItems: Array<{ title: string; body: string }>
  rangeLabel: string
}

type RankedEvidence = { evidence: ActivationEvidence; impact: number; backendOrder: number }

const HORIZON_LIMITS: Record<WhyTimeHorizonId, number> = { long: 3, medium: 2, fast: 1 }
const HORIZON_RANGES: Record<WhyTimeHorizonId, string> = {
  long: "1 год → несколько лет",
  medium: "2–6 месяцев вокруг пика",
  fast: "несколько часов → 2 суток",
}
const LONG_HORIZON_TECHNIQUES = new Set(["annual_profection", "firdar_major", "firdar_minor", "solar_return"])
const MEDIUM_HORIZON_TECHNIQUES = new Set(["monthly_profection", "lunar_return", "secondary_progression", "solar_arc", "eclipse_window"])
const FAST_TRANSIT_PLANETS = new Set(["MOON", "SUN", "MERCURY", "VENUS", "MARS"])
const SLOW_TRANSIT_PLANETS = new Set(["JUPITER", "SATURN", "URANUS", "NEPTUNE", "PLUTO"])
const PHASE_PRIORITY: Record<string, number> = { exact: 4, applying: 3, separating: 2, background: 1, period: 1 }

// START_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getEvidenceDurationLabel
// purpose: Return a conservative typical duration from structured evidence.
// inputs: evidence — backend-owned activation evidence.
// returns: Localized duration without invented calendar dates.
// side_effects: none.
// emitted_logs: none.
// error_behavior: unknown values use a neutral orientation label.
// END_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getEvidenceDurationLabel
export function getEvidenceDurationLabel(evidence: Pick<ActivationEvidence, "technique" | "sourcePlanet">): string {
  const durations: Record<string, string> = {
    annual_profection: "От дня рождения до следующего · около 12 месяцев",
    monthly_profection: "Обычно около месяца",
    firdar_major: "Обычно несколько лет",
    firdar_minor: "Вложенный период · от нескольких месяцев до нескольких лет",
    solar_return: "От одного дня рождения до следующего",
    lunar_return: "Обычно около 27–28 дней",
    secondary_progression: "Ориентировочно месяцы вокруг точного контакта",
    solar_arc: "Ориентировочно месяцы вокруг точного контакта",
    eclipse_window: "Несколько недель до и после затмения",
  }
  if (durations[evidence.technique]) return durations[evidence.technique]
  const planet = planetCanonKey(evidence.sourcePlanet)
  if (planet === "MOON") return "Обычно несколько часов → 2 суток"
  if (["SUN", "MERCURY", "VENUS"].includes(planet || "")) return "Обычно несколько дней → 2 недели"
  if (planet === "MARS") return "Обычно несколько дней → 4 недели"
  if (planet === "JUPITER") return "Ориентировочно 1–4 месяца"
  if (planet === "SATURN") return "Ориентировочно 3–9 месяцев"
  if (["URANUS", "NEPTUNE", "PLUTO"].includes(planet || "")) return "2–6 месяцев вокруг пика · возможны повторные волны дольше"
  return "Ориентировочный период зависит от конкретного сигнала"
}

// START_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getEvidenceStageLabel
// purpose: Translate a backend phase into a human technical-card stage label.
// inputs: phase — backend activation phase.
// returns: Localized stage label or null.
// side_effects: none.
// emitted_logs: none.
// error_behavior: unknown phase returns null.
// END_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getEvidenceStageLabel
export function getEvidenceStageLabel(phase: string | null | undefined): string | null {
  const labels: Record<string, string> = {
    exact: "Пик — сейчас",
    applying: "Набирает силу",
    separating: "Пик уже пройден · влияние ослабевает",
    background: "Фон уже действует",
    period: "Фон уже действует",
  }
  return phase ? labels[phase] || null : null
}

function getProfectionTargetDescription(evidence: ActivationEvidence): string {
  if (evidence.targetType === "planet") {
    const planet = [evidence.targetPlanet, evidence.targetKey]
      .map(planetCanonKey)
      .map((key) => key ? PLANET_LABELS_NOMINATIVE[key] : null)
      .find(Boolean)
    return planet ? `темы ${planet}` : "активной личной темы"
  }
  if (evidence.targetType === "house") return "активной жизненной сферы"
  if (evidence.targetType === "angle") return "личного направления и способа проявляться"
  if (evidence.targetType === "lot") return "чувствительной точки карты"
  if (evidence.targetType === "sphere") return SPHERE_CONCISE[evidence.targetKey] || "активной личной темы"
  return "активной личной темы"
}

// START_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getTechnicalEvidenceExplanation
// purpose: Explain known technique, planets, and aspect without fatalistic copy.
// inputs: evidence — structured backend activation evidence.
// returns: Technique definition and contextual meaning.
// side_effects: none.
// emitted_logs: none.
// error_behavior: unknown identifiers use safe generic explanations.
// END_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getTechnicalEvidenceExplanation
export function getTechnicalEvidenceExplanation(evidence: ActivationEvidence): { definition: string; meaning: string } {
  const definitions: Record<string, string> = {
    transit_to_natal: "Транзит — это фактическое положение планеты сейчас. Расчёт сравнивает его с натальной картой — положением планет в момент вашего рождения — и помогает понять, почему личная тема становится заметнее именно в текущий период.",
    transit_to_angle: "Транзит сопоставляет текущее положение планеты с ASC, MC или другим углом карты — чувствительной точкой личного направления и проявления.",
    transit_to_lot: "Транзит сопоставляет текущее положение планеты с расчётной чувствительной точкой карты, которую в традиции называют жребием.",
    transit_planet_in_house: "Этот расчёт показывает прохождение планеты по жизненной сфере дома и помогает увидеть, где тема заметнее в текущем периоде.",
    annual_profection: `Профекция — календарная техника: с каждым днём рождения акцент переходит к следующей теме карты и её управителю. Она не обещает событие; здесь показывает годовой фокус ${getProfectionTargetDescription(evidence)}.`,
    monthly_profection: "Месячная профекция уточняет, какая тема карты получает дополнительный акцент в текущем коротком цикле. Она не обещает событие.",
    firdar_major: "Фирдар — традиционное деление жизни на большие планетарные периоды. Он не обещает событие; здесь независимо подтверждает долгий фон той же темы.",
    firdar_minor: "Младший фирдар — вложенный период внутри более длинного жизненного фона. Он не обещает событие, а уточняет его текущий акцент.",
    solar_return: "Карта возвращения Солнца к натальному положению задаёт фон личного года и помогает увидеть его приоритетные темы.",
    lunar_return: "Карта возвращения Луны к натальному положению описывает короткий месячный фон и его текущие акценты.",
    secondary_progression: "Вторичная прогрессия описывает медленное внутреннее разворачивание личной темы и не обещает внешнего события.",
    solar_arc: "Солнечная дуга сравнивает синхронное символическое смещение точек карты, чтобы заметить медленно созревающую тему.",
    eclipse_window: "Окно затмения отмечает период повышенного внимания к уже назревшей теме, не обещая конкретного события.",
  }
  const planetCopy: Record<string, string> = {
    SUN: "Солнце связано с ощущением направления, воли и заметности личной позиции.",
    MOON: "Луна показывает быстрый эмоциональный и телесный отклик.",
    MERCURY: "Меркурий связан с мыслями, разговорами, документами и способом договориться.",
    VENUS: "Венера связана с ценностями, отношениями, симпатией и тем, что приносит удовольствие.",
    MARS: "Марс связан с импульсом действовать, защищать границы и направлять энергию.",
    JUPITER: "Юпитер связан с расширением возможностей, смыслом и тем, где хочется видеть больше перспективы.",
    SATURN: "Сатурн связан со структурой, границами, ответственностью и проверяемой опорой.",
    URANUS: "Уран связан с потребностью обновить привычный способ действовать и дать месту для нового решения.",
    NEPTUNE: "Нептун может размывать старую ясность и просит сверять ощущения с фактами.",
    PLUTO: "Плутон связан с глубокой перестройкой, силой и отношением к контролю.",
  }
  const aspectCopy: Record<string, string> = {
    conjunction: "Соединение собирает две темы в одном фокусе.",
    sextile: "Секстиль создаёт возможность взаимодействия, которую важно заметить и использовать.",
    square: "Квадрат показывает трение, которое можно разобрать через конкретные действия.",
    trine: "Тригон позволяет согласовать две темы с меньшим трением, но не является автоматическим подарком.",
    opposition: "Оппозиция показывает два полюса, которым нужен осознанный баланс, а не борьба.",
  }
  const planets = [planetCopy[planetCanonKey(evidence.sourcePlanet) || ""], planetCopy[planetCanonKey(evidence.targetPlanet) || ""]].filter(Boolean).join(" ")
  const aspect = aspectCopy[(evidence.aspect || "").toLowerCase()] || "Сигнал помогает заметить текущий личный акцент без обещания события."
  const orbMeaning = evidence.orb != null && evidence.orb <= 1
    ? "Небольшой орб означает, что этот технический контакт сейчас расположен близко к точному положению, поэтому его удобно рассматривать как заметный акцент периода."
    : "Орб показывает техническую дистанцию до точного положения и помогает понять, насколько контакт близок к пику."
  return {
    definition: definitions[evidence.technique] || "Это один из расчётных способов увидеть, как личная тема проявляется во времени.",
    meaning: [planets, aspect, evidence.orb != null ? orbMeaning : null].filter(Boolean).join(" "),
  }
}

function contributionImpact(v2: TodayV2Block, evidenceId: string): number {
  return Object.values(v2.scoreBreakdown).flatMap((score) => score.contributions)
    .filter((contribution) => contribution.source === "activation" && contribution.sourceId === evidenceId)
    .reduce((sum, contribution) => sum + Math.abs(contribution.amount), 0)
}

function classifyHorizon(evidence: ActivationEvidence): WhyTimeHorizonId | null {
  if (LONG_HORIZON_TECHNIQUES.has(evidence.technique)) return "long"
  if (MEDIUM_HORIZON_TECHNIQUES.has(evidence.technique)) return "medium"
  if (evidence.kind === "period") return "long"
  if (evidence.technique.startsWith("transit")) {
    const planet = planetCanonKey(evidence.sourcePlanet)
    if (FAST_TRANSIT_PLANETS.has(planet || "")) return "fast"
    if (SLOW_TRANSIT_PLANETS.has(planet || "")) return "medium"
  }
  return evidence.kind === "aspect" && evidence.strength >= 0.5 ? "medium" : null
}

function passesHorizonThreshold(horizon: WhyTimeHorizonId, evidence: ActivationEvidence, impact: number, isWhyLinked: boolean): boolean {
  if (horizon === "long") return evidence.strength >= 0.45 || impact > 0 || isWhyLinked
  if (horizon === "medium") return evidence.strength >= 0.5 || impact >= 0.25
  if (!(["applying", "exact", "separating"] as string[]).includes(evidence.phase)) return false
  const planet = planetCanonKey(evidence.sourcePlanet)
  const maxOrb = planet === "MOON" || planet === "MARS" ? 2 : 1.5
  return (evidence.strength >= 0.65 || impact >= 0.35) && (evidence.orb == null || evidence.orb <= maxOrb)
}

// START_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.selectWhyTimeHorizons
// purpose: Select ranked, related V2 evidence into long/medium/fast time horizons.
// inputs: v2 — complete backend-owned V2 block.
// returns: Non-empty horizons in long → medium → fast order.
// side_effects: none.
// emitted_logs: none.
// error_behavior: returns an empty array rather than fabricating a signal.
// END_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.selectWhyTimeHorizons
export function selectWhyTimeHorizons(v2: TodayV2Block): WhyTimeHorizon[] {
  const primary = v2.activationSummary.topActivatedTargets[0]
  const active = v2.activationEvidence.filter((evidence) => evidence.active !== false)
  const primaryOrdered = orderActivationEvidence(active, primary)
  const hasUsablePrimaryEvidence = Boolean(primary?.activationIds.some((id) => active.some((evidence) => evidence.id === id)))
  const relatedIds = new Set([
    ...v2.whyToday.flatMap((item) => item.activationIds),
    ...Object.values(v2.scoreBreakdown).flatMap((score) => score.contributions)
      .filter((contribution) => contribution.source === "activation")
      .map((contribution) => contribution.sourceId),
  ])
  const whyLinkedIds = new Set(v2.whyToday.flatMap((item) => item.activationIds))
  const candidates = hasUsablePrimaryEvidence
    ? primaryOrdered
    : active.filter((evidence) => relatedIds.has(evidence.id))
  const ranked = candidates.map((evidence, backendOrder): RankedEvidence => ({ evidence, backendOrder, impact: contributionImpact(v2, evidence.id) }))
    .sort((left, right) => right.impact - left.impact || right.evidence.strength - left.evidence.strength || (PHASE_PRIORITY[right.evidence.phase] || 0) - (PHASE_PRIORITY[left.evidence.phase] || 0) || (left.evidence.orb ?? Infinity) - (right.evidence.orb ?? Infinity) || left.backendOrder - right.backendOrder)
  const selected: Record<WhyTimeHorizonId, RankedEvidence[]> = { long: [], medium: [], fast: [] }
  for (const item of ranked) {
    const horizon = classifyHorizon(item.evidence)
    if (!horizon || selected[horizon].length >= HORIZON_LIMITS[horizon]) continue
    if (passesHorizonThreshold(horizon, item.evidence, item.impact, whyLinkedIds.has(item.evidence.id))) selected[horizon].push(item)
  }
  const evidenceHorizon = new Map(selected.long.concat(selected.medium, selected.fast).map((item) => [item.evidence.id, item.evidence]))
  const horizonForWhy = (item: TodayV2WhyTodayItem): WhyTimeHorizonId | null => {
    const linked = ranked.find((candidate) => item.activationIds.includes(candidate.evidence.id) && evidenceHorizon.has(candidate.evidence.id))
    if (!linked) return null
    return (Object.entries(selected).find(([, items]) => items.some((item) => item.evidence.id === linked.evidence.id))?.[0] as WhyTimeHorizonId | undefined) || null
  }
  return (["long", "medium", "fast"] as WhyTimeHorizonId[]).map((id) => ({
    id,
    evidence: selected[id].map((item) => item.evidence),
    whyItems: v2.whyToday.filter((item) => horizonForWhy(item) === id).map(getSafeWhyTodayItem),
    rangeLabel: HORIZON_RANGES[id],
  })).filter((horizon) => horizon.evidence.length > 0)
}

// START_BLOCK: PREVIEW_TIMING_BRIDGE
export type EvidenceTimingPreview = {
  activeFrom: string | null | undefined
  exactAt: string | null | undefined
  activeUntil: string | null | undefined
}

// START_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getEvidenceTimingPreview
// purpose: Temporary preview timing bridge reader to retrieve activeFrom, exactAt, and activeUntil.
// inputs: evidence - ActivationEvidence (generated wire type).
// returns: EvidenceTimingPreview containing strings, nulls, or undefined.
// side_effects: none.
// emitted_logs: none.
// error_behavior: invalid activeFrom/activeUntil preview values become undefined; exactAt remains the generated typed value.
// END_FUNCTION_CONTRACT: F-M-LIB-PRESENTATION-TODAY-V2.getEvidenceTimingPreview
export function getEvidenceTimingPreview(
  evidence: ActivationEvidence | null | undefined,
): EvidenceTimingPreview {
  if (!evidence) {
    return { activeFrom: undefined, exactAt: undefined, activeUntil: undefined }
  }

  const exactAt = evidence.exactAt
  const activeFromVal = Reflect.get(evidence, "activeFrom")
  const activeUntilVal = Reflect.get(evidence, "activeUntil")

  const activeFrom = typeof activeFromVal === "string" || activeFromVal === null ? activeFromVal : undefined
  const activeUntil = typeof activeUntilVal === "string" || activeUntilVal === null ? activeUntilVal : undefined

  return { activeFrom, exactAt, activeUntil }
}
// END_BLOCK: PREVIEW_TIMING_BRIDGE
// END_BLOCK: HUMAN_FIRST_PRESENTATION
