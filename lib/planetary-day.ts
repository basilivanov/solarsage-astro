// ############################################################################
// AI_HEADER: MODULE_LIB_PLANETARY_DAY
// ROLE: Planetary day ruler computation (traditional Western astrology).
// DEPENDENCIES: none
// ############################################################################

/**
 * Planetary day ruler — in traditional Western astrology, each day of
 * the week is ruled by one of the 7 classical planets. The ruler sets
 * the "flavor" of the day.
 *
 * This is a fixed mapping based on the day of the week:
 *   Sunday    → Sun       (☉)
 *   Monday    → Moon      (☽)
 *   Tuesday   → Mars      (♂)
 *   Wednesday → Mercury   (☿)
 *   Thursday  → Jupiter   (♃)
 *   Friday    → Venus     (♀)
 *   Saturday  → Saturn    (♄)
 *
 * The planetary HOUR ruler changes every hour, but the day ruler is
 * fixed. We compute both for richness.
 */

export interface PlanetaryDayInfo {
  /** Day ruler planet (English) */
  dayRuler: string
  /** Day ruler Russian name */
  dayRulerRu: string
  /** Day ruler symbol */
  dayRulerSymbol: string
  /** Day ruler color */
  dayRulerColor: string
  /** Day of week in Russian */
  dayOfWeekRu: string
  /** Current planetary hour ruler (English) */
  hourRuler: string
  /** Current planetary hour ruler Russian name */
  hourRulerRu: string
  /** Current planetary hour ruler symbol */
  hourRulerSymbol: string
  /** Short interpretation of the day ruler */
  dayInterpretation: string
  /** Short interpretation of the current hour ruler */
  hourInterpretation: string
  /** Whether the current hour is a "day" hour (sunrise-based) or "night" hour */
  hourType: "day" | "night"
}

const DAY_RULERS = [
  { planet: "Sun", ru: "Солнце", symbol: "☉", color: "oklch(0.72 0.15 60)", dowRu: "Воскресенье", interpretation: "День самовыражения, личности, творчества. Хорошо для того, чтобы быть в центре внимания, проявлять щедрость." },
  { planet: "Moon", ru: "Луна", symbol: "☽", color: "oklch(0.62 0.04 295)", dowRu: "Понедельник", interpretation: "День эмоций, интуиции, дома, семьи. Хорошо для заботы, отдыха, бытовых дел." },
  { planet: "Mars", ru: "Марс", symbol: "♂", color: "oklch(0.58 0.18 27)", dowRu: "Вторник", interpretation: "День действия, энергии, смелости. Хорошо для спорта, инициативы, решения сложных задач." },
  { planet: "Mercury", ru: "Меркурий", symbol: "☿", color: "oklch(0.62 0.08 230)", dowRu: "Среда", interpretation: "День коммуникации, учёбы, торговли. Хорошо для переговоров, документов, обучения." },
  { planet: "Jupiter", ru: "Юпитер", symbol: "♃", color: "oklch(0.70 0.13 85)", dowRu: "Четверг", interpretation: "День расширения, удачи, мудрости. Хорошо для крупных начинаний, обучения, путешествий." },
  { planet: "Venus", ru: "Венера", symbol: "♀", color: "oklch(0.70 0.12 15)", dowRu: "Пятница", interpretation: "День любви, красоты, партнёрства. Хорошо для свиданий, искусства, покупок, примирения." },
  { planet: "Saturn", ru: "Сатурн", symbol: "♄", color: "oklch(0.55 0.05 260)", dowRu: "Суббота", interpretation: "День дисциплины, ответственности, подведения итогов. Хорошо для уборки, планирования, рутинных дел." },
]

const HOUR_RULER_INTERPRETATIONS: Record<string, string> = {
  Sun: "Час активности и самовыражения",
  Moon: "Час эмоций и интуиции",
  Mars: "Час действия и решительности",
  Mercury: "Час общения и информации",
  Jupiter: "Час удачи и расширения",
  Venus: "Час красоты и притяжения",
  Saturn: "Час дисциплины и структуры",
}

const PLANET_META: Record<string, { ru: string; symbol: string; color: string }> = {
  Sun: { ru: "Солнце", symbol: "☉", color: "oklch(0.72 0.15 60)" },
  Moon: { ru: "Луна", symbol: "☽", color: "oklch(0.62 0.04 295)" },
  Mars: { ru: "Марс", symbol: "♂", color: "oklch(0.58 0.18 27)" },
  Mercury: { ru: "Меркурий", symbol: "☿", color: "oklch(0.62 0.08 230)" },
  Jupiter: { ru: "Юпитер", symbol: "♃", color: "oklch(0.70 0.13 85)" },
  Venus: { ru: "Венера", symbol: "♀", color: "oklch(0.70 0.12 15)" },
  Saturn: { ru: "Сатурн", symbol: "♄", color: "oklch(0.55 0.05 260)" },
}

// Planetary hour sequence: day hours follow one order, night hours another.
// The Chaldean order: Saturn, Jupiter, Mars, Sun, Venus, Mercury, Moon.
// Day starts at sunrise with the day ruler, then follows the sequence.
const CHALDEAN_ORDER = ["Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon"]

/**
 * Compute the planetary day and hour ruler for a given date.
 * Uses sunrise at ~6:00 local as a simplified approximation (real
 * computation needs actual sunrise time for the observer's location).
 */
export function getPlanetaryDay(date: Date): PlanetaryDayInfo {
  const dow = date.getDay() // 0=Sunday, 6=Saturday
  const dayRuler = DAY_RULERS[dow]

  // Simplified sunrise: 6:00 local. Day hours = 6:00-18:00, night hours = 18:00-6:00.
  // Each period has 12 hours of varying length. For simplicity, use equal 60-min hours.
  const hours = date.getHours()
  const minutes = date.getMinutes()
  const hourType: "day" | "night" = hours >= 6 && hours < 18 ? "day" : "night"

  // Hour index within the current period (0-11)
  const hourInPeriod = hours >= 6 && hours < 18
    ? hours - 6
    : hours >= 18
      ? hours - 18
      : hours + 6 // 0-5 maps to 6-11 of night period

  // The first hour of the day period is ruled by the day ruler.
  // Subsequent hours follow the Chaldean order.
  const dayRulerIndex = CHALDEAN_ORDER.indexOf(dayRuler.planet)
  const hourRulerIndex = (dayRulerIndex + hourInPeriod) % 7
  const hourRuler = CHALDEAN_ORDER[hourRulerIndex]
  const hourMeta = PLANET_META[hourRuler]

  return {
    dayRuler: dayRuler.planet,
    dayRulerRu: dayRuler.ru,
    dayRulerSymbol: dayRuler.symbol,
    dayRulerColor: dayRuler.color,
    dayOfWeekRu: dayRuler.dowRu,
    hourRuler,
    hourRulerRu: hourMeta.ru,
    hourRulerSymbol: hourMeta.symbol,
    dayInterpretation: dayRuler.interpretation,
    hourInterpretation: HOUR_RULER_INTERPRETATIONS[hourRuler] ?? "",
    hourType,
  }
}

export interface PlanetaryHourEntry {
  /** Hour index within the period (0-11) */
  index: number
  /** Hour ruler planet (English) */
  ruler: string
  /** Hour ruler Russian name */
  rulerRu: string
  /** Hour ruler symbol */
  rulerSymbol: string
  /** Hour ruler color */
  rulerColor: string
  /** Start time as Date */
  startsAt: Date
  /** End time as Date */
  endsAt: Date
  /** Whether this is the current hour */
  isCurrent: boolean
  /** Whether this is a day or night hour */
  type: "day" | "night"
}

/**
 * Compute the full 12-hour timeline for the current planetary period
 * (day or night). The first hour is ruled by the day ruler; subsequent
 * hours follow the Chaldean order.
 */
export function getPlanetaryHourTimeline(date: Date): PlanetaryHourEntry[] {
  const dow = date.getDay()
  const dayRuler = DAY_RULERS[dow]
  const dayRulerIndex = CHALDEAN_ORDER.indexOf(dayRuler.planet)

  const hours = date.getHours()
  const hourType: "day" | "night" = hours >= 6 && hours < 18 ? "day" : "night"
  const currentHourInPeriod = hours >= 6 && hours < 18
    ? hours - 6
    : hours >= 18
      ? hours - 18
      : hours + 6

  const periodStartHour = hourType === "day" ? 6 : 18
  const entries: PlanetaryHourEntry[] = []

  for (let i = 0; i < 12; i++) {
    const rulerIndex = (dayRulerIndex + i) % 7
    const ruler = CHALDEAN_ORDER[rulerIndex]
    const meta = PLANET_META[ruler]
    const startHour = (periodStartHour + i) % 24
    const endHour = (periodStartHour + i + 1) % 24

    const startDateTime = new Date(date)
    startDateTime.setHours(startHour, 0, 0, 0)
    const endDateTime = new Date(date)
    endDateTime.setHours(endHour, 0, 0, 0)

    entries.push({
      index: i,
      ruler,
      rulerRu: meta.ru,
      rulerSymbol: meta.symbol,
      rulerColor: meta.color,
      startsAt: startDateTime,
      endsAt: endDateTime,
      isCurrent: i === currentHourInPeriod,
      type: hourType,
    })
  }

  return entries
}
