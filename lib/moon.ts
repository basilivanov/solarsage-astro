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

/**
 * Traditional 29 lunar days. Each day has a specific quality and meaning
 * in Russian astrological tradition. The 30th day is "empty" — it exists
 * only in some months and is considered unfavorable.
 *
 * The lunar day starts at sunrise (in the simplified model we use the
 * age-based computation: lunar day N spans age (N-1)..N days since the
 * last new moon, with day 30 being the "leftover" partial day).
 */
export interface LunarDayInfo {
  /** Day number 1..30 (30 is the "empty" day if present) */
  day: number
  /** Short Russian name/quality of the day */
  name: string
  /** Detailed Russian description of the day's energy */
  description: string
  /** Whether the day is considered favorable overall */
  favorable: boolean
  /** Element/quality tag for color coding */
  tag: "светлый" | "нейтральный" | "напряжённый" | "тёмный"
}

const LUNAR_DAYS: LunarDayInfo[] = [
  { day: 1, name: "День замысла", description: "Чистый лист. Хорошо закладывать намерения, планировать, медитировать. Не начинать важных дел сразу.", favorable: true, tag: "светлый" },
  { day: 2, name: "День притока сил", description: "Накопление энергии. Полезны простые рутинные дела, забота о теле, питание.", favorable: true, tag: "светлый" },
  { day: 3, name: "День активности", description: "Энергия бьёт ключом. Хорошо для спорта, путешествий, начинаний. Избегать агрессии.", favorable: true, tag: "нейтральный" },
  { day: 4, name: "День выбора", description: "Переломный момент цикла. Решения, принятые сегодня, надолго определят путь.", favorable: true, tag: "нейтральный" },
  { day: 5, name: "День доверия", description: "Энергия устойчива. Хорошо для работы с информацией, учёбы, наставничества.", favorable: true, tag: "светлый" },
  { day: 6, name: "День слова", description: "Слова сегодня имеют особую силу. Хорошо для молитв, аффирмаций, обещаний.", favorable: true, tag: "светлый" },
  { day: 7, name: "День тишины", description: "Лучше молчать и слушать. Избегать ссор, не принимать резких решений.", favorable: false, tag: "напряжённый" },
  { day: 8, name: "День очищения", description: "Хорошо для очищения пространства, тела, мыслей. Прощение и отпускание.", favorable: true, tag: "светлый" },
  { day: 9, name: "День очищения", description: "Продолжение очищения. Избегать конфликтов, опасных дел, резких движений.", favorable: false, tag: "напряжённый" },
  { day: 10, name: "День традиций", description: "Связь с родом и предками. Хорошо для семейных дел, ритуалов, рукоделия.", favorable: true, tag: "светлый" },
  { day: 11, name: "День силы", description: "Энергия мощная. Хорошо для амбициозных дел, тренировок, презентаций.", favorable: true, tag: "светлый" },
  { day: 12, name: "День милосердия", description: "Доброта и помощь другим. Пожертвования, благотворительность, забота.", favorable: true, tag: "светлый" },
  { day: 13, name: "День коллективного", description: "Групповая работа, сообщества, друзья. Избегать одиночных амбиций.", favorable: true, tag: "нейтральный" },
  { day: 14, name: "День творчества", description: "Прилив вдохновения. Творчество, искусство, новые идеи. Хорошо для свиданий.", favorable: true, tag: "светлый" },
  { day: 15, name: "День искушения", description: "Полнолуние. Эмоции на пике. Избегать ссор, импульсивных решений, алкоголя.", favorable: false, tag: "напряжённый" },
  { day: 16, name: "День гармонии", description: "Равновесие после полнолуния. Хорошо для партнёрства, красоты, искусства.", favorable: true, tag: "светлый" },
  { day: 17, name: "День радости", description: "Энергия радости и изобилия. Праздники, встречи, наслаждение жизнью.", favorable: true, tag: "светлый" },
  { day: 18, name: "День зеркал", description: "Всё возвращается. Избегать зла, делать добро. Хорошо для рефлексии.", favorable: false, tag: "напряжённый" },
  { day: 19, name: "День чистоты", description: "Очищение разума и пространства. Избегать ссор и негативных мыслей.", favorable: true, tag: "нейтральный" },
  { day: 20, name: "День выбора пути", description: "Важные решения. Хорошо для планирования будущего, медитации.", favorable: true, tag: "нейтральный" },
  { day: 21, name: "День прощения", description: "Очищение кармы. Прощение, отпускание обид. Избегать жадности.", favorable: true, tag: "светлый" },
  { day: 22, name: "День знаний", description: "Хорошо для учёбы, новых знаний, открытия тайн. Мудрость доступна.", favorable: true, tag: "светлый" },
  { day: 23, name: "День смирения", description: "Принятие и спокойствие. Избегать амбиций, спешки, насилия.", favorable: false, tag: "напряжённый" },
  { day: 24, name: "День силы воли", description: "Сильная воля и дисциплина. Хорошо для сложных задач, тренировок.", favorable: true, tag: "нейтральный" },
  { day: 25, name: "День тишины", description: "Спокойствие и пассивность. Хорошо для отдыха, медитации, сна.", favorable: false, tag: "напряжённый" },
  { day: 26, name: "День намерений", description: "Планирование, загадывание желаний, работа с намерением.", favorable: true, tag: "нейтральный" },
  { day: 27, name: "День удачи", description: "Удача и интуиция. Хорошо для новых начинаний, сделок, озарений.", favorable: true, tag: "светлый" },
  { day: 28, name: "День воды", description: "Энергия воды и эмоций. Хорошо для отдыха у воды, прощения, медитации.", favorable: true, tag: "нейтральный" },
  { day: 29, name: "День подведения итогов", description: "Закрытие цикла. Прощание с прошлым, благодарность, отдых.", favorable: true, tag: "нейтральный" },
  { day: 30, name: "День пустоты", description: "Тёмный день. Избегать любых начинаний. Лучше молчать, спать, поститься.", favorable: false, tag: "тёмный" },
]

/**
 * Compute the traditional lunar day number (1-30) for a given date.
 * Uses the age since the last new moon: day N spans age (N-1)..N.
 * Day 30 only exists when the synodic month is long enough to contain it.
 */
export function getLunarDay(date: Date): LunarDayInfo {
  const m = computeMoonPhase(date)
  const day = Math.min(30, Math.floor(m.age) + 1)
  return LUNAR_DAYS[day - 1] ?? LUNAR_DAYS[0]
}

// ── Void-of-Course (VoC) Moon ──────────────────────────────────────
//
// The Moon is "void of course" when it makes no more major Ptolemaic
// aspects (conjunction, sextile, square, trine, opposition) to other
// planets before leaving its current sign. Traditionally considered a
// time to avoid starting new ventures — things initiated during VoC
// tend not to come to fruition.
//
// This is a simplified model: we compute the Moon's longitude and
// check whether it's within a "quiet zone" near the end of a sign
// (last 2° before the sign boundary). Real VoC computation requires
// full ephemeris aspect tracking.

export interface VoidOfCourseInfo {
  /** Whether the moon is currently void of course */
  isVoid: boolean
  /** When the current VoC period started (or null if not VoC) */
  startedAt: Date | null
  /** When the moon enters the next sign (end of VoC) */
  endsAt: Date | null
  /** Duration of the current VoC in hours (if VoC) */
  durationHours: number | null
  /** Short human-readable note */
  note: string
  /** Recommended action during VoC */
  recommendation: string
}

/**
 * Simplified VoC detection: the moon is considered VoC when it's
 * within the last ~2° of its sign AND the next major aspect is the
 * sign ingress. We approximate by checking if moon longitude mod 30
 * is >= 28 (i.e. within 2° of the next sign boundary).
 *
 * Real VoC periods last anywhere from a few minutes to ~24 hours and
 * occur every 2-3 days. This approximation flags ~6-7% of time as VoC.
 */
export function getVoidOfCourse(date: Date): VoidOfCourseInfo {
  const m = computeMoonPhase(date)
  // Moon's longitude within its current sign (0-30°)
  const moonLongInSign = (m.age / SYNODIC_MONTH) * 360 % 30
  // Simplified: VoC when moon is in last 2° of sign
  const isVoid = moonLongInSign >= 28

  if (!isVoid) {
    return {
      isVoid: false,
      startedAt: null,
      endsAt: null,
      durationHours: null,
      note: "Луна активна",
      recommendation: "Можно начинать новые дела и принимать решения.",
    }
  }

  // Moon moves ~0.55°/hour. Degrees until sign ingress:
  const degreesToIngress = 30 - moonLongInSign
  const hoursToIngress = degreesToIngress / 0.55
  // Approximate VoC start: 2° ago = ~3.6 hours ago
  const vocDurationHours = 2 / 0.55 + hoursToIngress
  const startedAt = new Date(date.getTime() - (vocDurationHours - hoursToIngress) * 3600000)
  const endsAt = new Date(date.getTime() + hoursToIngress * 3600000)

  return {
    isVoid: true,
    startedAt,
    endsAt,
    durationHours: Math.round(vocDurationHours * 10) / 10,
    note: "Луна без курса",
    recommendation: "Не начинай новое. Заверши начатое, отдохни, помедитируй. Решения, принятые сейчас, могут не сбыться.",
  }
}
