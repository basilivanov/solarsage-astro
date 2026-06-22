"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Orbit, ChevronRight } from "lucide-react"

/**
 * TransitTimeline — upcoming major planetary transits widget.
 *
 * Shows a vertical timeline of the next 12 months of significant
 * transits (Saturn return, Jupiter return, major outer-planet aspects)
 * computed from the user's natal planet positions.
 *
 * Uses simplified mean-motion ephemeris from J2000 epoch — accurate
 * enough for a demo. Real transit dates would come from the SolarSage
 * sidecar with Swiss Ephemeris.
 */

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}

const PLANET_RU: Record<string, string> = {
  Sun: "Солнце", Moon: "Луна", Mercury: "Меркурий", Venus: "Венера",
  Mars: "Марс", Jupiter: "Юпитер", Saturn: "Сатурн",
  Uranus: "Уран", Neptune: "Нептун", Pluto: "Плутон",
}

const PLANET_COLORS: Record<string, string> = {
  Sun: "oklch(0.72 0.15 60)", Moon: "oklch(0.62 0.04 295)",
  Mercury: "oklch(0.62 0.08 230)", Venus: "oklch(0.70 0.12 15)",
  Mars: "oklch(0.58 0.18 27)", Jupiter: "oklch(0.70 0.13 85)",
  Saturn: "oklch(0.55 0.05 260)", Uranus: "oklch(0.68 0.10 200)",
  Neptune: "oklch(0.62 0.10 270)", Pluto: "oklch(0.45 0.08 300)",
}

// Mean daily motion in degrees (J2000)
const MEAN_MOTION: Record<string, number> = {
  Sun: 0.9856, Moon: 13.1764, Mercury: 1.3833, Venus: 0.5240,
  Mars: 0.5240, Jupiter: 0.0831, Saturn: 0.0335,
  Uranus: 0.0117, Neptune: 0.0060, Pluto: 0.0040,
}

// J2000 epoch longitudes (degrees, tropical)
const J2000_LONGITUDE: Record<string, number> = {
  Sun: 280.0, Moon: 218.0, Mercury: 252.0, Venus: 181.0,
  Mars: 355.0, Jupiter: 34.0, Saturn: 50.0,
  Uranus: 314.0, Neptune: 304.0, Pluto: 247.0,
}

// Natal planet longitudes from DEMO_NATAL_RESPONSE
const NATAL_LONGITUDES: Record<string, number> = {
  Sun: 294.5, Moon: 129.1, Mercury: 267.6, Venus: 310.7,
  Mars: 253.4, Jupiter: 94.3, Saturn: 289.0,
  Uranus: 285.2, Neptune: 281.6, Pluto: 222.3,
}

const ASPECT_TONES: Record<number, { name: string; tone: "soft" | "hard" | "neutral"; color: string }> = {
  0: { name: "Соединение", tone: "neutral", color: "oklch(0.55 0.10 305)" },
  60: { name: "Секстиль", tone: "soft", color: "oklch(0.65 0.13 145)" },
  90: { name: "Квадрат", tone: "hard", color: "oklch(0.65 0.15 27)" },
  120: { name: "Трин", tone: "soft", color: "oklch(0.65 0.13 145)" },
  180: { name: "Оппозиция", tone: "hard", color: "oklch(0.65 0.15 27)" },
}

const TRANSIT_INTERPRETATIONS: Record<string, string> = {
  "Saturn-0": "Возвращение Сатурна — момент итогов и перестройки на ближайшие 29 лет. Время взросления и ответственности.",
  "Saturn-90": "Квадрат Сатурна — кризис роста, проверка на прочность. Период напряжённой работы над собой.",
  "Saturn-180": "Оппозиция Сатурна — середина цикла, точка выбора. Пересмотр обязательств.",
  "Jupiter-0": "Возвращение Юпитера — новый 12-летний цикл удачи и расширения. Время больших начинаний.",
  "Jupiter-90": "Квадрат Юпитера — корректировка курса. Проверка амбиций реальностью.",
  "Jupiter-120": "Трин Юпитера — гармоничный период роста и возможностей.",
  "Uranus-90": "Квадрат Урана — кризис освобождения, внезапные перемены. Потребность в свободе.",
  "Neptune-120": "Трин Нептуна — вдохновение, творческий подъём, духовная ясность.",
  "Pluto-0": "Возвращение Плутона — трансформация идентичности. Глубинная перестройка (раз в 248 лет).",
  "Pluto-90": "Квадрат Плутона — мощная трансформация, освобождение от старого.",
}

type Transit = {
  date: Date
  transitingPlanet: string
  natalPlanet: string
  aspect: number
  exact: boolean
  interpretation: string
}

function computeTransits(startDate: Date, monthsAhead: number): Transit[] {
  const transits: Transit[] = []
  const endTime = new Date(startDate)
  endTime.setMonth(endTime.getMonth() + monthsAhead)

  // For each outer planet (Jupiter through Pluto) + Saturn, check transits to natal Sun, Moon, Mercury, Venus, Mars
  const transitingPlanets = ["Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]
  const natalTargets = ["Sun", "Moon", "Mercury", "Venus", "Mars"]

  const dayMs = 86400000
  const totalDays = Math.ceil((endTime.getTime() - startDate.getTime()) / dayMs)

  for (const tp of transitingPlanets) {
    const motion = MEAN_MOTION[tp]
    const j2000 = J2000_LONGITUDE[tp]
    for (const np of natalTargets) {
      const natalLong = NATAL_LONGITUDES[np]
      // Check each day for aspect formation
      let lastAspectDay = -100
      for (let d = 0; d <= totalDays; d++) {
        const date = new Date(startDate.getTime() + d * dayMs)
        const daysSinceJ2000 = (date.getTime() - Date.UTC(2000, 0, 1, 12)) / dayMs
        const transitingLong = (j2000 + motion * daysSinceJ2000) % 360
        const diff = ((transitingLong - natalLong + 540) % 360) - 180

        for (const aspect of [0, 60, 90, 120, 180]) {
          const orb = Math.abs(diff - aspect)
          if (orb < 1.0 && d - lastAspectDay > 30) {
            // Only include "major" transits: Saturn aspects + Jupiter conjunction + outer planet major aspects
            const key = `${tp}-${aspect}`
            const interpretation = TRANSIT_INTERPRETATIONS[key]
            if (!interpretation && !(tp === "Saturn" && (aspect === 0 || aspect === 90 || aspect === 180))) continue
            if (!interpretation && !(tp === "Jupiter" && (aspect === 0 || aspect === 120))) continue
            if (!interpretation) continue

            transits.push({
              date,
              transitingPlanet: tp,
              natalPlanet: np,
              aspect,
              exact: true,
              interpretation,
            })
            lastAspectDay = d
            break
          }
        }
      }
    }
  }

  // Sort by date and take first 8
  transits.sort((a, b) => a.date.getTime() - b.date.getTime())
  return transits.slice(0, 8)
}

function formatDate(d: Date): string {
  const months = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
  return `${d.getDate()} ${months[d.getMonth()]} ${d.getFullYear()}`
}

export function TransitTimeline() {
  const [expanded, setExpanded] = useState<string | null>(null)

  const transits = useMemo(() => computeTransits(new Date(), 12), [])

  if (transits.length === 0) return null

  return (
    <section className="px-5 pt-6" aria-label="Транзиты">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          <Orbit className="h-3 w-3" strokeWidth={1.8} />
          Ближайшие транзиты
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-card">
        {/* Timeline line */}
        <div
          aria-hidden
          className="pointer-events-none absolute left-[26px] top-3 bottom-3 w-px bg-gradient-to-b from-border via-border/50 to-transparent"
        />

        <ol className="relative space-y-0">
          {transits.map((t, i) => {
            const aspectMeta = ASPECT_TONES[t.aspect]
            const transitingColor = PLANET_COLORS[t.transitingPlanet]
            const natalColor = PLANET_COLORS[t.natalPlanet]
            const isExpanded = expanded === `${i}`
            const isLast = i === transits.length - 1

            return (
              <li key={`${t.transitingPlanet}-${t.natalPlanet}-${t.date.toISOString()}`}>
                <button
                  type="button"
                  onClick={() => setExpanded(isExpanded ? null : `${i}`)}
                  className={`group flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-muted/30 ${isLast ? "" : "border-b border-border/40"}`}
                >
                  {/* Timeline dot */}
                  <div className="relative z-10 mt-0.5 flex-none">
                    <div
                      className="flex h-7 w-7 items-center justify-center rounded-full border-2 bg-card"
                      style={{ borderColor: transitingColor }}
                    >
                      <span className="text-[11px] leading-none" style={{ color: transitingColor }}>
                        {PLANET_SYMBOLS[t.transitingPlanet]}
                      </span>
                    </div>
                  </div>

                  {/* Content */}
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[12.5px] font-medium text-foreground">
                        {PLANET_RU[t.transitingPlanet]} → {PLANET_SYMBOLS[t.natalPlanet]} {PLANET_RU[t.natalPlanet]}
                      </span>
                      <span className="flex-none text-[11px] tabular-nums text-muted-foreground">
                        {formatDate(t.date)}
                      </span>
                    </div>
                    <div className="mt-1 flex items-center gap-2">
                      <span
                        className="inline-flex items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-medium"
                        style={{ color: aspectMeta.color, background: `${aspectMeta.color}14` }}
                      >
                        {aspectMeta.name}
                      </span>
                      <span className="text-[11px] leading-snug text-muted-foreground truncate">
                        {t.interpretation.slice(0, 60)}…
                      </span>
                    </div>

                    <AnimatePresence initial={false}>
                      {isExpanded && (
                        <motion.div
                          initial={{ height: 0, opacity: 0 }}
                          animate={{ height: "auto", opacity: 1 }}
                          exit={{ height: 0, opacity: 0 }}
                          transition={{ duration: 0.2 }}
                          className="overflow-hidden"
                        >
                          <p className="mt-2 text-[12px] leading-relaxed text-foreground/80">
                            {t.interpretation}
                          </p>
                          <div className="mt-2 flex items-center gap-3 text-[10px] text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <span style={{ color: transitingColor }}>{PLANET_SYMBOLS[t.transitingPlanet]}</span>
                              {PLANET_RU[t.transitingPlanet]} транзит
                            </span>
                            <span aria-hidden>·</span>
                            <span className="flex items-center gap-1">
                              <span style={{ color: natalColor }}>{PLANET_SYMBOLS[t.natalPlanet]}</span>
                              {PLANET_RU[t.natalPlanet]} натальный
                            </span>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  <ChevronRight
                    className={`mt-1 h-3.5 w-3.5 flex-none text-muted-foreground transition-transform ${isExpanded ? "rotate-90" : ""}`}
                    strokeWidth={1.8}
                  />
                </button>
              </li>
            )
          })}
        </ol>
      </div>

      <p className="mt-2 text-center text-[10px] text-muted-foreground/60">
        Демо-расчёт по средним движениям. Точные даты требуют эфемерид.
      </p>
    </section>
  )
}
