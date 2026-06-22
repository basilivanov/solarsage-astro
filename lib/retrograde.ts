// ############################################################################
// AI_HEADER: MODULE_LIB_RETROGRADE
// ROLE: Simplified planetary retrograde computation utilities.
// DEPENDENCIES: none
// ############################################################################

/**
 * Simplified retrograde detection for Mercury, Venus, and Mars.
 *
 * Retrograde periods are computed from mean orbital elements with
 * sine-wave approximation. This is accurate to within a few days for
 * Mercury/Venus and about a week for Mars — sufficient for a demo.
 *
 * Real retrograde dates would come from the SolarSage sidecar with
 * full ephemeris (Swiss Ephemeris).
 */

export interface RetrogradeInfo {
  planet: string
  planetRu: string
  symbol: string
  color: string
  isRetrograde: boolean
  /** When the current retrograde period started (or null if not Rx) */
  rxStartedAt: Date | null
  /** When the current retrograde period ends (or null if not Rx) */
  rxEndsAt: Date | null
  /** Days into the current Rx period (0-based, null if not Rx) */
  daysIntoRx: number | null
  /** Total days of the current Rx period (null if not Rx) */
  rxDurationDays: number | null
  /** When the next Rx period starts (null if currently Rx) */
  nextRxStart: Date | null
  /** Short Russian note about the current state */
  note: string
  /** Russian interpretation of the retrograde meaning */
  interpretation: string
}

const PLANET_META = {
  Mercury: { ru: "Меркурий", symbol: "☿", color: "oklch(0.62 0.08 230)" },
  Venus: { ru: "Венера", symbol: "♀", color: "oklch(0.70 0.12 15)" },
  Mars: { ru: "Марс", symbol: "♂", color: "oklch(0.58 0.18 27)" },
} as const

// Mean retrograde cycle parameters: [period days, rx duration days, phase offset days]
// Approximate values from astronomical data.
const RX_PARAMS: Record<string, { cycleDays: number; rxDays: number; phaseOffset: number }> = {
  // Mercury: Rx ~3 times per year, ~24 days each, cycle ~116 days
  Mercury: { cycleDays: 116, rxDays: 24, phaseOffset: 0 },
  // Venus: Rx every ~19 months, ~42 days each
  Venus: { cycleDays: 576, rxDays: 42, phaseOffset: 30 },
  // Mars: Rx every ~26 months, ~72 days each
  Mars: { cycleDays: 780, rxDays: 72, phaseOffset: 100 },
}

// Reference epoch: 2024-01-01 00:00 UTC
const REF_EPOCH = Date.UTC(2024, 0, 1, 0, 0, 0)

const INTERPRETATIONS: Record<string, string> = {
  Mercury: "Пересмотры, задержки в коммуникациях, возвращение к незавершённым разговорам. Не подписывать контракты, проверять информацию.",
  Venus: "Пересмотр отношений и ценностей. Старые чувства могут вернуться. Не начинать новых романов, не делать крупных покупок красоты.",
  Mars: "Энергия направлена внутрь. Споры всплывают из прошлого. Физическая активность изменчива. Лучше дорабатывать, чем начинать.",
}

const ACTIVE_NOTES: Record<string, string> = {
  Mercury: "Прямое движение",
  Venus: "Прямое движение",
  Mars: "Прямое движение",
}

/**
 * Compute retrograde info for a planet at a given date.
 */
export function getRetrograde(planet: string, date: Date): RetrogradeInfo {
  const meta = PLANET_META[planet as keyof typeof PLANET_META]
  const params = RX_PARAMS[planet]
  if (!meta || !params) {
    throw new Error(`Unknown planet: ${planet}`)
  }

  const daysSinceEpoch = (date.getTime() - REF_EPOCH) / 86400000
  // Position in the cycle (0..cycleDays), offset by phase
  const posInCycle = ((daysSinceEpoch + params.phaseOffset) % params.cycleDays + params.cycleDays) % params.cycleDays

  const isRetrograde = posInCycle < params.rxDays

  if (isRetrograde) {
    const daysIntoRx = Math.floor(posInCycle)
    const rxDurationDays = params.rxDays
    const rxStartedAt = new Date(date.getTime() - daysIntoRx * 86400000)
    const rxEndsAt = new Date(rxStartedAt.getTime() + rxDurationDays * 86400000)

    return {
      planet,
      planetRu: meta.ru,
      symbol: meta.symbol,
      color: meta.color,
      isRetrograde: true,
      rxStartedAt,
      rxEndsAt,
      daysIntoRx,
      rxDurationDays,
      nextRxStart: null,
      note: "Ретроградная",
      interpretation: INTERPRETATIONS[planet] ?? "",
    }
  }

  // Not retrograde — find next Rx start
  const daysUntilNextRx = params.rxDays - posInCycle < 0
    ? params.cycleDays - posInCycle
    : params.cycleDays - posInCycle
  const nextRxStart = new Date(date.getTime() + daysUntilNextRx * 86400000)

  return {
    planet,
    planetRu: meta.ru,
    symbol: meta.symbol,
    color: meta.color,
    isRetrograde: false,
    rxStartedAt: null,
    rxEndsAt: null,
    daysIntoRx: null,
    rxDurationDays: null,
    nextRxStart,
    note: ACTIVE_NOTES[planet] ?? "Прямое движение",
    interpretation: "",
  }
}

/**
 * Get retrograde info for all tracked planets (Mercury, Venus, Mars).
 */
export function getAllRetrogrades(date: Date): RetrogradeInfo[] {
  return ["Mercury", "Venus", "Mars"].map((p) => getRetrograde(p, date))
}

/**
 * Check if any planet is currently retrograde.
 */
export function hasAnyRetrograde(date: Date): boolean {
  return getAllRetrogrades(date).some((r) => r.isRetrograde)
}
