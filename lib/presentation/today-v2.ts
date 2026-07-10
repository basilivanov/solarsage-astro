// ############################################################################
// AI_HEADER: MODULE_LIB_PRESENTATION_TODAY_V2
// ROLE: Presentation-only localization/formatting for Today V2 structured fields.
//       No scoring, convergence, or astrology calculation.
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-PRESENTATION-TODAY-V2
// purpose: Localize and format backend-owned V2 activation evidence fields for UI.
// owns:
//   - lib/presentation/today-v2.ts
// inputs: structured V2 evidence / technique / sphere / phase fields
// outputs: Russian labels and human evidence titles
// dependencies: none (pure presentation)
// side_effects: none
// emitted_logs: none
// invariants:
//   - Never computes scores, convergence, or importance
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
// semantic_blocks:
//   - LABELS: planet/aspect/phase/technique/sphere maps
//   - FORMATTERS: human evidence titles
//   - SELECTION: presentation-only evidence selection
// owned_tests:
//   - __tests__/lib/presentation/today-v2.test.ts
// END_MODULE_MAP: M-LIB-PRESENTATION-TODAY-V2

import type { ActivationEvidence, TodayV2ActivatedTarget } from "@/lib/contracts/today"

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
