// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_TONE
// ROLE: Tone normalization and styling helper for synastry components
// DEPENDENCIES: none
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-TONE
// purpose: Provide single source of truth for synastry tone normalization and color classes.
// owns:
//   - components/synastry/synastry-tone.ts
// inputs: raw tone string
// outputs: NormalizedSynastryTone ("good" | "mid" | "bad") and display labels/styles
// dependencies: none
// side_effects: none
// emitted_logs: none
// failure_policy: defaults to "mid"
// END_MODULE_CONTRACT: M-SYNASTRY-TONE

// START_MODULE_MAP: M-SYNASTRY-TONE
// public_entrypoints:
//   - normalizeSynastryTone
//   - getToneStatusLabel
//   - getRelationLabel
// semantic_blocks: none
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-TONE

export type NormalizedSynastryTone = "good" | "mid" | "bad"

export function normalizeSynastryTone(value: string | null | undefined): NormalizedSynastryTone {
  const str = (value || "").toLowerCase()
  if (["good", "supportive", "harmony"].includes(str)) return "good"
  if (["bad", "tense", "tension"].includes(str)) return "bad"
  return "mid"
}

export function getToneContactLabel(tone: NormalizedSynastryTone): string {
  switch (tone) {
    case "good":
      return "поддерживающий контакт"
    case "bad":
      return "напряжённый контакт"
    case "mid":
    default:
      return "неоднозначный контакт"
  }
}

export function getToneStatusLabel(tone: NormalizedSynastryTone): string {
  switch (tone) {
    case "good":
      return "Хорошо подходит"
    case "bad":
      return "Сложно"
    case "mid":
    default:
      return "Нормально"
  }
}

export function getRelationLabel(relation: string | null | undefined): string {
  const rel = (relation || "").toLowerCase()
  switch (rel) {
    case "romantic":
      return "Романтические отношения"
    case "friend":
      return "Дружба"
    case "business":
    case "work":
      return "Работа"
    case "family":
      return "Семья"
    default:
      if (!relation) return "Отношения"
      return relation.charAt(0).toUpperCase() + relation.slice(1)
  }
}
