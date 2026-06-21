// ############################################################################
// AI_HEADER: MODULE_LIB_MOON
// ROLE: Pure astronomical moon-phase computation utilities.
//   Shared by MoonPhaseWidget (Today) and LunarCalendarStrip (Calendar).
// DEPENDENCIES: none
// ############################################################################

/**
 * Known new-moon epoch: 2000-01-06 18:14 UTC (J2000 reference new moon).
 * Used as the anchor for the mean synodic month calculation.
 */
export const NEW_MOON_EPOCH = Date.UTC(2000, 0, 6, 18, 14, 0)

/** Mean synodic month (days) — average from new moon to new moon. */
export const SYNODIC_MONTH = 29.530588853

export interface MoonPhaseInfo {
  /** 0=new, 1=waxing crescent, 2=first quarter, 3=waxing gibbous, 4=full, 5=waning gibbous, 6=last quarter, 7=waning crescent */
  phaseIndex: number
  /** Illuminated percentage 0-100 */
  illumination: number
  /** Days since the last new moon (0..29.53) */
  age: number
  /** Human-readable Russian phase name */
  phaseName: string
  /** Emoji glyph for the phase */
  phaseEmoji: string
  /** Short interpretation of the phase */
  phaseShort: string
  /** Moon zodiac sign index 0-11 (Aries=0..Pisces=11) */
  signIndex: number
  /** Moon zodiac sign Russian name */
  signName: string
  /** Moon zodiac sign symbol */
  signSymbol: string
  /** Element of the sign: Огонь/Земля/Воздух/Вода */
  signElement: string
  /** True if the moon is waxing (growing), false if waning */
  isWaxing: boolean
  /** Fraction of the synodic cycle completed (0..1) */
  cycleFraction: number
}

const PHASES = [
  { name: "Новолуние", emoji: "🌑", short: "Время начинаний и намерений" },
  { name: "Растущий серп", emoji: "🌒", short: "Рост, первые шаги к цели" },
  { name: "Первая четверть", emoji: "🌓", short: "Решительность и действие" },
  { name: "Растущая Луна", emoji: "🌔", short: "Усиление и приближение к пиковой энергии" },
  { name: "Полнолуние", emoji: "🌕", short: "Пик эмоций, кульминация, ясность" },
  { name: "Убывающая Луна", emoji: "🌖", short: "Подведение итогов, благодарность" },
  { name: "Последняя четверть", emoji: "🌗", short: "Освобождение, пересмотр" },
  { name: "Убывающий серп", emoji: "🌘", short: "Отдых, рефлексия, закрытие цикла" },
] as const

const ZODIAC_SIGNS = [
  { name: "Овен", symbol: "♈", element: "Огонь" },
  { name: "Телец", symbol: "♉", element: "Земля" },
  { name: "Близнецы", symbol: "♊", element: "Воздух" },
  { name: "Рак", symbol: "♋", element: "Вода" },
  { name: "Лев", symbol: "♌", element: "Огонь" },
  { name: "Дева", symbol: "♍", element: "Земля" },
  { name: "Весы", symbol: "♎", element: "Воздух" },
  { name: "Скорпион", symbol: "♏", element: "Вода" },
  { name: "Стрелец", symbol: "♐", element: "Огонь" },
  { name: "Козерог", symbol: "♑", element: "Земля" },
  { name: "Водолей", symbol: "♒", element: "Воздух" },
  { name: "Рыбы", symbol: "♓", element: "Вода" },
] as const

/**
 * Compute the moon phase for a given date.
 * Uses the mean synodic month from a known new-moon epoch — accurate
 * to ±1 day, which is sufficient for a demo. The real SolarSage sidecar
 * would use Swiss Ephemeris for arc-minute precision.
 */
export function computeMoonPhase(date: Date): MoonPhaseInfo {
  const now = date.getTime()
  const ageDays =
    (((now - NEW_MOON_EPOCH) / 86400000) % SYNODIC_MONTH + SYNODIC_MONTH) %
    SYNODIC_MONTH
  const phaseFraction = ageDays / SYNODIC_MONTH
  const illumination = Math.round(
    ((1 - Math.cos(2 * Math.PI * phaseFraction)) / 2) * 100,
  )

  // Phase index: 0=new, 1=waxing crescent, 2=first quarter, 3=waxing gibbous,
  // 4=full, 5=waning gibbous, 6=last quarter, 7=waning crescent
  let phaseIndex: number
  if (illumination < 2) phaseIndex = phaseFraction < 0.5 ? 0 : 4
  else if (illumination >= 98) phaseIndex = 4
  else if (phaseFraction < 0.25) phaseIndex = 1
  else if (phaseFraction < 0.5) phaseIndex = 3
  else if (phaseFraction < 0.75) phaseIndex = 5
  else phaseIndex = 7
  // Snap to quarter phases
  if (illumination >= 48 && illumination <= 52) {
    phaseIndex = phaseFraction < 0.5 ? 2 : 6
  }

  const phase = PHASES[phaseIndex]

  // Moon zodiac sign: moon spends ~2.5 days per sign. Approximate by
  // dividing the lunar cycle into 12 segments offset from epoch.
  const signIndex = Math.floor(((ageDays / SYNODIC_MONTH) * 12 + 3) % 12)
  const sign = ZODIAC_SIGNS[signIndex]

  return {
    phaseIndex,
    illumination,
    age: ageDays,
    phaseName: phase.name,
    phaseEmoji: phase.emoji,
    phaseShort: phase.short,
    signIndex,
    signName: sign.name,
    signSymbol: sign.symbol,
    signElement: sign.element,
    isWaxing: phaseFraction < 0.5,
    cycleFraction: phaseFraction,
  }
}

/**
 * Compute the moon phase for a date at midnight UTC.
 * Useful for calendars where each day needs a stable phase.
 */
export function computeMoonPhaseForDay(
  year: number,
  month: number,
  day: number,
): MoonPhaseInfo {
  const date = new Date(Date.UTC(year, month, day, 12, 0, 0))
  return computeMoonPhase(date)
}

/**
 * Get a compact moon-phase summary for calendar display.
 * Returns the emoji + illumination % for quick rendering.
 */
export function getMoonPhaseCompact(date: Date): { emoji: string; illumination: number; phaseIndex: number } {
  const m = computeMoonPhase(date)
  return { emoji: m.phaseEmoji, illumination: m.illumination, phaseIndex: m.phaseIndex }
}

/**
 * Check if a date is a "lunar event" day (new moon, full moon, or quarter).
 * These are the most visually meaningful phases for a calendar.
 */
export function isLunarEventDay(date: Date): boolean {
  const m = computeMoonPhase(date)
  return [0, 2, 4, 6].includes(m.phaseIndex)
}

/**
 * Get the lunar event name for a date, or null if it's not an event day.
 */
export function getLunarEventName(date: Date): string | null {
  const m = computeMoonPhase(date)
  switch (m.phaseIndex) {
    case 0: return "Новолуние"
    case 2: return "Первая четверть"
    case 4: return "Полнолуние"
    case 6: return "Последняя четверть"
    default: return null
  }
}
