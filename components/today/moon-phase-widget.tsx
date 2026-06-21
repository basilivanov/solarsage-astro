"use client"

import { useMemo, useState } from "react"
import { motion } from "framer-motion"
import { getLunarDay, type LunarDayInfo } from "@/lib/moon"

/**
 * MoonPhaseWidget — shows the current moon phase, illumination %,
 * zodiac sign, and a short interpretation.
 *
 * Calculation is a simplified astronomical approximation based on the
 * mean synodic month (29.53059 days) from a known new-moon epoch.
 * Accurate enough for a demo (±1 day); the real SolarSage sidecar
 * would use Swiss Ephemeris.
 */

const NEW_MOON_EPOCH = Date.UTC(2000, 0, 6, 18, 14, 0) // 2000-01-06 18:14 UTC, known new moon
const SYNODIC_MONTH = 29.530588853 // days

const PHASES = [
  { name: "Новолуние", emoji: "🌑", illumRange: [0, 2], short: "Время начинаний и намерений" },
  { name: "Растущий серп", emoji: "🌒", illumRange: [2, 48], short: "Рост, первые шаги к цели" },
  { name: "Первая четверть", emoji: "🌓", illumRange: [48, 52], short: "Решительность и действие" },
  { name: "Растущая Луна", emoji: "🌔", illumRange: [52, 98], short: "Усиление и приближение к пиковой энергии" },
  { name: "Полнолуние", emoji: "🌕", illumRange: [98, 100], short: "Пик эмоций, кульминация, ясность" },
  { name: "Убывающая Луна", emoji: "🌖", illumRange: [52, 98], short: "Подведение итогов, благодарность" },
  { name: "Последняя четверть", emoji: "🌗", illumRange: [48, 52], short: "Освобождение, пересмотр" },
  { name: "Убывающий серп", emoji: "🌘", illumRange: [2, 48], short: "Отдых, рефлексия, закрытие цикла" },
]

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
]

interface MoonPhaseWidgetProps {
  /** The date to compute the moon phase for. Defaults to now. */
  date?: Date
}

function computeMoonPhase(date: Date): {
  phaseIndex: number
  illumination: number
  age: number // days since new moon
  phaseName: string
  phaseEmoji: string
  phaseShort: string
  signIndex: number
  signName: string
  signSymbol: string
  signElement: string
  isWaxing: boolean
} {
  const now = date.getTime()
  const ageDays = (((now - NEW_MOON_EPOCH) / 86400000) % SYNODIC_MONTH + SYNODIC_MONTH) % SYNODIC_MONTH
  const phaseFraction = ageDays / SYNODIC_MONTH
  // Illumination (0-100): half-cycle cosine
  const illumination = Math.round((1 - Math.cos(2 * Math.PI * phaseFraction)) / 2 * 100)

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
  }
}

const ELEMENT_COLORS: Record<string, string> = {
  "Огонь": "oklch(0.65 0.15 27)",
  "Земля": "oklch(0.55 0.08 150)",
  "Воздух": "oklch(0.62 0.08 230)",
  "Вода": "oklch(0.60 0.10 260)",
}

export function MoonPhaseWidget({ date }: MoonPhaseWidgetProps) {
  const [expanded, setExpanded] = useState(false)
  const moon = useMemo(() => computeMoonPhase(date ?? new Date()), [date])
  const lunarDay = useMemo(() => getLunarDay(date ?? new Date()), [date])

  return (
    <section className="px-6" aria-label="Луна сегодня">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Луна сегодня
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="group relative w-full overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/30 p-4 text-left transition-all hover:border-border active:scale-[0.99]"
        aria-expanded={expanded}
      >
        {/* night-sky backdrop */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-40"
          style={{
            background:
              "radial-gradient(circle at 80% 20%, oklch(0.6 0.08 260 / 0.12), transparent 50%), radial-gradient(circle at 20% 80%, oklch(0.55 0.06 295 / 0.10), transparent 50%)",
          }}
        />
        {/* tiny stars */}
        <div aria-hidden className="pointer-events-none absolute inset-0">
          {[12, 28, 45, 67, 82, 91].map((left, i) => (
            <motion.span
              key={i}
              className="absolute h-0.5 w-0.5 rounded-full bg-foreground/30"
              style={{ left: `${left}%`, top: `${15 + (i * 11) % 70}%` }}
              animate={{ opacity: [0.2, 0.8, 0.2] }}
              transition={{ duration: 2 + i * 0.4, repeat: Infinity, delay: i * 0.3 }}
            />
          ))}
        </div>

        <div className="relative flex items-center gap-4">
          {/* Moon visual */}
          <div className="relative flex h-16 w-16 flex-none items-center justify-center">
            <MoonVisual phaseIndex={moon.phaseIndex} illumination={moon.illumination} />
            {/* Lunar day number badge */}
            <span
              className="engraved-badge absolute -bottom-1 -right-1 flex h-6 w-6 items-center justify-center rounded-full text-[10px] font-bold tabular-nums text-foreground"
              title={`Лунный день ${lunarDay.day}`}
            >
              {lunarDay.day}
            </span>
          </div>

          {/* Phase info */}
          <div className="min-w-0 flex-1">
            <div className="flex items-baseline justify-between gap-2">
              <span className="font-serif text-[18px] leading-tight text-foreground">
                {moon.phaseName}
              </span>
              <span className="text-[11px] tabular-nums text-muted-foreground">
                {moon.illumination}%
              </span>
            </div>
            <div className="mt-1 flex flex-wrap items-center gap-1.5">
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  color: ELEMENT_COLORS[moon.signElement],
                  background: `${ELEMENT_COLORS[moon.signElement]}14`,
                }}
              >
                {moon.signSymbol} {moon.signName}
              </span>
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  color: LUNAR_TAG_COLORS[lunarDay.tag],
                  background: `${LUNAR_TAG_COLORS[lunarDay.tag]}14`,
                }}
                title={lunarDay.name}
              >
                {lunarDay.day} лунный день
              </span>
            </div>
            <p className="mt-1.5 text-[11.5px] leading-snug text-muted-foreground">
              {lunarDay.name}. {moon.phaseShort}
            </p>
          </div>
        </div>

        {/* Expandable detail */}
        <motion.div
          initial={false}
          animate={{ height: expanded ? "auto" : 0, opacity: expanded ? 1 : 0 }}
          transition={{ duration: 0.25 }}
          className="overflow-hidden"
        >
          <div className="mt-3.5 space-y-2 border-t border-border/50 pt-3">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-muted-foreground">Лунный день</span>
              <span className="text-foreground">
                {lunarDay.day} — {lunarDay.name}
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-muted-foreground">Возраст Луны</span>
              <span className="tabular-nums text-foreground">{moon.age.toFixed(1)} дн.</span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-muted-foreground">Фаза цикла</span>
              <span className="text-foreground">
                {moon.isWaxing ? "Растущая" : "Убывающая"} · {Math.round((moon.age / SYNODIC_MONTH) * 100)}%
              </span>
            </div>
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-muted-foreground">Следующее полнолуние</span>
              <span className="tabular-nums text-foreground">
                ~{Math.max(0, Math.round(SYNODIC_MONTH - moon.age - (moon.isWaxing ? moon.age : 0)))} дн.
              </span>
            </div>
            {/* Lunar day quality */}
            <div
              className="rounded-lg px-3 py-2 text-[11px] leading-relaxed"
              style={{
                background: `${LUNAR_TAG_COLORS[lunarDay.tag]}10`,
                color: LUNAR_TAG_COLORS[lunarDay.tag],
              }}
            >
              <div className="mb-0.5 flex items-center gap-1.5">
                <span
                  className="h-1.5 w-1.5 rounded-full"
                  style={{ background: LUNAR_TAG_COLORS[lunarDay.tag] }}
                />
                <span className="text-[10px] font-medium uppercase tracking-[0.1em]">
                  {lunarDay.favorable ? "благоприятный" : "осторожный"} · {lunarDay.tag}
                </span>
              </div>
              <p className="text-foreground/80">{lunarDay.description}</p>
            </div>
            <div className="rounded-lg bg-secondary/40 px-3 py-2 text-[11px] leading-relaxed text-muted-foreground">
              <span className="font-medium text-foreground">{moon.signSymbol} Луна в {moon.signName}.</span>{" "}
              {signInterpretation(moon.signName)}
            </div>
          </div>
        </motion.div>

        <div className="mt-2 text-center text-[10px] text-muted-foreground/70">
          {expanded ? "↑ свернуть" : "↓ подробнее"}
        </div>
      </button>
    </section>
  )
}

const LUNAR_TAG_COLORS: Record<LunarDayInfo["tag"], string> = {
  "светлый": "oklch(0.65 0.13 145)",
  "нейтральный": "oklch(0.62 0.06 230)",
  "напряжённый": "oklch(0.65 0.15 60)",
  "тёмный": "oklch(0.45 0.05 295)",
}

function signInterpretation(sign: string): string {
  const interpretations: Record<string, string> = {
    "Овен": "Эмоции яркие и непосредственные. Хочется действовать и брать инициативу.",
    "Телец": "Потребность в стабильности и комфорте. Спокойствие важнее перемен.",
    "Близнецы": "Желание общаться и узнавать новое. Эмоции меняются быстро.",
    "Рак": "Чувствительность и связь с домом. Глубокая интуиция.",
    "Лев": "Потребность в признании и тепле. Хочется быть в центре внимания.",
    "Дева": "Стремление к порядку и полезности. Эмоции сдерживаются.",
    "Весы": "Жажда гармонии и партнёрства. Избегание конфликтов.",
    "Скорпион": "Глубина и интенсивность. Скрытность, трансформация чувств.",
    "Стрелец": "Желание свободы и смысла. Оптимизм, поиск перспектив.",
    "Козерог": "Сдержанность и ответственность. Эмоции под контролем.",
    "Водолей": "Независимость и оригинальность. Эмоции через интеллект.",
    "Рыбы": "Чувствительность и эмпатия. Границы размыты, сильна интуиция.",
  }
  return interpretations[sign] ?? ""
}

/**
 * Pure SVG moon phase visual. Draws the illuminated portion as a
 * clipped shape based on the phase index and illumination.
 */
function MoonVisual({ phaseIndex, illumination }: { phaseIndex: number; illumination: number }) {
  // Size of the moon
  const R = 28
  const size = R * 2

  // For phases 0 (new) and 4 (full), we can use simple fills.
  // For crescent/gibbous, we use two overlapping ellipses with clip.
  // phaseIndex: 0=new, 1=waxing crescent, 2=first quarter, 3=waxing gibbous,
  //             4=full, 5=waning gibbous, 6=last quarter, 7=waning crescent

  const isFull = phaseIndex === 4
  const isNew = phaseIndex === 0
  const isWaxingPhase = phaseIndex === 1 || phaseIndex === 2 || phaseIndex === 3
  const isQuarter = phaseIndex === 2 || phaseIndex === 6
  const isCrescent = phaseIndex === 1 || phaseIndex === 7
  const isGibbous = phaseIndex === 3 || phaseIndex === 5

  // The terminator ellipse width factor (0..1): at quarter it's 0, at new/full it's 1
  const terminatorWidth = isQuarter ? 0 : Math.abs(Math.cos((illumination / 100) * Math.PI))

  // Shadow side: waxing → left half dark; waning → right half dark
  const darkOnLeft = isWaxingPhase || phaseIndex === 4

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="h-16 w-16">
      <defs>
        <radialGradient id="moon-light" cx="35%" cy="35%" r="65%">
          <stop offset="0%" stopColor="oklch(0.97 0.015 85)" />
          <stop offset="80%" stopColor="oklch(0.92 0.015 85)" />
          <stop offset="100%" stopColor="oklch(0.85 0.02 85)" />
        </radialGradient>
        <radialGradient id="moon-dark" cx="65%" cy="65%" r="65%">
          <stop offset="0%" stopColor="oklch(0.30 0.02 295)" />
          <stop offset="100%" stopColor="oklch(0.20 0.02 295)" />
        </radialGradient>
        <filter id="moon-glow">
          <feGaussianBlur stdDeviation="1.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Outer glow */}
      <circle cx={R} cy={R} r={R} fill="oklch(0.85 0.04 260 / 0.15)" filter="url(#moon-glow)" />

      {isNew ? (
        // New moon: mostly dark with thin outline
        <>
          <circle cx={R} cy={R} r={R - 1} fill="url(#moon-dark)" />
          <circle cx={R} cy={R} r={R - 1} fill="none" stroke="oklch(0.4 0.03 295 / 0.4)" strokeWidth={0.5} />
        </>
      ) : isFull ? (
        // Full moon: fully lit
        <>
          <circle cx={R} cy={R} r={R - 1} fill="url(#moon-light)" />
          {/* craters */}
          <circle cx={R - 6} cy={R - 4} r={2} fill="oklch(0.82 0.015 85 / 0.5)" />
          <circle cx={R + 4} cy={R + 2} r={3} fill="oklch(0.82 0.015 85 / 0.4)" />
          <circle cx={R + 2} cy={R - 6} r={1.5} fill="oklch(0.82 0.015 85 / 0.5)" />
          <circle cx={R - 3} cy={R + 5} r={1.2} fill="oklch(0.82 0.015 85 / 0.5)" />
        </>
      ) : (
        // Partial phases: clip the lit portion
        <>
          <defs>
            <clipPath id={`moon-clip-${phaseIndex}`}>
              {isCrescent || isGibbous ? (
                // Crescent: lit area is the intersection of two ellipses
                // Gibbous: lit area is the union minus a crescent
                <path
                  d={describeMoonShape(R, terminatorWidth, darkOnLeft, isGibbous)}
                />
              ) : isQuarter ? (
                // Quarter: half circle
                <path
                  d={darkOnLeft
                    ? `M ${R} 0 A ${R} ${R} 0 0 1 ${R} ${size} L ${R} 0 Z`
                    : `M ${R} 0 A ${R} ${R} 0 0 0 ${R} ${size} L ${R} 0 Z`}
                />
              ) : (
                <circle cx={R} cy={R} r={R} />
              )}
            </clipPath>
          </defs>
          {/* Dark base (whole moon) */}
          <circle cx={R} cy={R} r={R - 1} fill="url(#moon-dark)" />
          {/* Lit portion clipped */}
          <g clipPath={`url(#moon-clip-${phaseIndex})`}>
            <circle cx={R} cy={R} r={R - 1} fill="url(#moon-light)" />
            {/* subtle craters on lit side */}
            <circle cx={darkOnLeft ? R + 4 : R - 6} cy={R - 3} r={1.5} fill="oklch(0.82 0.015 85 / 0.4)" />
            <circle cx={darkOnLeft ? R + 2 : R - 3} cy={R + 4} r={2} fill="oklch(0.82 0.015 85 / 0.3)" />
          </g>
        </>
      )}

      {/* Outline */}
      <circle cx={R} cy={R} r={R - 0.5} fill="none" stroke="oklch(0.5 0.03 295 / 0.25)" strokeWidth={0.5} />
    </svg>
  )
}

/**
 * Build an SVG path for the illuminated crescent or gibbous shape.
 * The moon is centered at (R, R) with radius R.
 * - terminatorWidth: 0..1, how wide the terminator ellipse is (0=quarter, 1=new/full)
 * - darkOnLeft: true for waxing (right side lit), false for waning (left side lit)
 * - isGibbous: if true, lit area is the large (>50%) portion
 */
function describeMoonShape(R: number, terminatorWidth: number, darkOnLeft: boolean, isGibbous: boolean): string {
  const cx = R
  const cy = R
  const rx = R * Math.max(0.05, terminatorWidth)
  // Outer arc: half of the moon circle
  // We trace the lit area: outer semicircle + terminator ellipse arc
  const litOnRight = darkOnLeft // waxing → lit on right
  // Outer semicircle from top to bottom on the lit side
  const outerStart = litOnRight ? `M ${cx} ${cy - R}` : `M ${cx} ${cy - R}`
  const outerArc = litOnRight
    ? `A ${R} ${R} 0 0 1 ${cx} ${cy + R}`
    : `A ${R} ${R} 0 0 0 ${cx} ${cy + R}`
  // Terminator arc back to top
  // For crescent: terminator bulges toward lit side (sweep same as outer)
  // For gibbous: terminator bulges away from lit side (sweep opposite)
  const sweep = isGibbous ? (litOnRight ? 0 : 1) : (litOnRight ? 1 : 0)
  const terminatorArc = `A ${rx} ${R} 0 0 ${sweep} ${cx} ${cy - R}`
  return `${outerStart} ${outerArc} ${terminatorArc} Z`
}
