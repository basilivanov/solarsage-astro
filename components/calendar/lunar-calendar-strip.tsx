"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Moon, CalendarDays, Info } from "lucide-react"
import { computeMoonPhaseForDay, type MoonPhaseInfo } from "@/lib/moon"

/**
 * LunarCalendarStrip — moon-phase visualization for the Calendar screen.
 *
 * Renders a horizontal scrollable strip of moon phases for the entire
 * month, highlighting the four key lunar events (new moon, first quarter,
 * full moon, last quarter). Tapping a day shows the phase details.
 *
 * Designed to sit above the day-status calendar grid as a complementary
 * "lunar layer" — users can see at a glance which days carry lunar weight.
 */

interface LunarCalendarStripProps {
  year: number
  month: number // 0-indexed
}

const PHASE_COLORS: Record<number, string> = {
  0: "oklch(0.30 0.02 295)", // new moon — deep
  1: "oklch(0.60 0.04 295)", // waxing crescent
  2: "oklch(0.55 0.06 305)", // first quarter — plum
  3: "oklch(0.65 0.05 305)", // waxing gibbous
  4: "oklch(0.72 0.08 85)",  // full moon — gold
  5: "oklch(0.65 0.05 305)", // waning gibbous
  6: "oklch(0.55 0.06 305)", // last quarter — plum
  7: "oklch(0.60 0.04 295)", // waning crescent
}

const PHASE_NAMES_RU = [
  "Новолуние", "Растущий серп", "Первая четверть", "Растущая Луна",
  "Полнолуние", "Убывающая Луна", "Последняя четверть", "Убывающий серп",
]

function daysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

export function LunarCalendarStrip({ year, month }: LunarCalendarStripProps) {
  const [selectedDay, setSelectedDay] = useState<number | null>(null)

  const phases = useMemo(() => {
    const total = daysInMonth(year, month)
    return Array.from({ length: total }, (_, i) => {
      const day = i + 1
      const info = computeMoonPhaseForDay(year, month, day)
      return { day, info }
    })
  }, [year, month])

  // Find the four key lunar events this month
  const keyEvents = useMemo(() => {
    const events: { day: number; phaseIndex: number; name: string }[] = []
    let lastPhase = -1
    for (const p of phases) {
      // Event days: 0, 2, 4, 6
      if ([0, 2, 4, 6].includes(p.info.phaseIndex) && p.info.phaseIndex !== lastPhase) {
        events.push({
          day: p.day,
          phaseIndex: p.info.phaseIndex,
          name: PHASE_NAMES_RU[p.info.phaseIndex],
        })
        lastPhase = p.info.phaseIndex
      }
    }
    return events
  }, [phases])

  const selected = selectedDay !== null ? phases.find((p) => p.day === selectedDay) : null

  return (
    <section className="px-5 pt-4" aria-label="Лунный календарь">
      <div className="rounded-2xl border border-border/50 bg-gradient-to-br from-card via-card to-secondary/20 p-4">
        {/* Header */}
        <div className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Moon className="h-3.5 w-3.5 text-primary" strokeWidth={1.75} />
            <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              Лунный календарь
            </h3>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] text-muted-foreground/70">
            <CalendarDays className="h-3 w-3" strokeWidth={1.75} />
            <span>{phases.length} дней</span>
          </div>
        </div>

        {/* Key lunar events this month */}
        {keyEvents.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {keyEvents.map((e) => {
              const color = PHASE_COLORS[e.phaseIndex]
              return (
                <button
                  key={e.day}
                  type="button"
                  onClick={() => setSelectedDay(e.day)}
                  className="inline-flex items-center gap-1 rounded-full border px-2 py-1 text-[10px] font-medium transition active:scale-95"
                  style={{
                    borderColor: `${color}30`,
                    background: `${color}0d`,
                    color,
                  }}
                >
                  <PhaseGlyph phaseIndex={e.phaseIndex} size={10} />
                  <span>{e.name}</span>
                  <span className="tabular-nums opacity-70">{e.day}</span>
                </button>
              )
            })}
          </div>
        )}

        {/* Moon phase strip — scrollable */}
        <div className="-mx-1 overflow-x-auto px-1 pb-1">
          <div className="flex gap-1.5" style={{ minWidth: "min-content" }}>
            {phases.map(({ day, info }) => {
              const isEvent = [0, 2, 4, 6].includes(info.phaseIndex)
              const isSelected = selectedDay === day
              const color = PHASE_COLORS[info.phaseIndex]
              return (
                <button
                  key={day}
                  type="button"
                  onClick={() => setSelectedDay(isSelected ? null : day)}
                  className="flex flex-col items-center gap-1 rounded-lg px-1.5 py-1.5 transition active:scale-95"
                  style={{
                    background: isSelected ? `${color}14` : "transparent",
                    outline: isEvent ? `1px solid ${color}30` : "none",
                  }}
                  aria-label={`${day} — ${PHASE_NAMES_RU[info.phaseIndex]}, ${info.illumination}%`}
                  title={`${day} — ${PHASE_NAMES_RU[info.phaseIndex]} (${info.illumination}%)`}
                >
                  <span className="text-[9px] tabular-nums text-muted-foreground">
                    {day}
                  </span>
                  <PhaseGlyph phaseIndex={info.phaseIndex} size={20} />
                  <span
                    className="text-[8px] tabular-nums leading-none"
                    style={{ color: isEvent ? color : "oklch(0.55 0.02 295)" }}
                  >
                    {info.illumination}%
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* Selected day detail */}
        <AnimatePresence>
          {selected && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="mt-3 rounded-lg border border-border/50 bg-background/60 p-3">
                <div className="flex items-center gap-3">
                  <PhaseGlyph phaseIndex={selected.info.phaseIndex} size={36} />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-sm font-medium text-foreground">
                        {selected.info.phaseName}
                      </span>
                      <span className="text-[11px] tabular-nums text-muted-foreground">
                        {selected.day}.{month + 1} · {selected.info.illumination}%
                      </span>
                    </div>
                    <p className="mt-0.5 text-[11px] leading-snug text-muted-foreground">
                      {selected.info.phaseShort}
                    </p>
                    <div className="mt-1.5 flex items-center gap-1.5">
                      <span
                        className="inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[9px] font-medium"
                        style={{
                          color: PHASE_COLORS[selected.info.phaseIndex],
                          background: `${PHASE_COLORS[selected.info.phaseIndex]}14`,
                        }}
                      >
                        {selected.info.signSymbol} {selected.info.signName}
                      </span>
                      <span className="text-[9px] text-muted-foreground">
                        {selected.info.signElement}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Legend */}
        <div className="mt-2.5 flex items-center justify-center gap-3 text-[9px] text-muted-foreground/70">
          <span className="inline-flex items-center gap-1">
            <PhaseGlyph phaseIndex={0} size={9} />
            новолуние
          </span>
          <span className="inline-flex items-center gap-1">
            <PhaseGlyph phaseIndex={4} size={9} />
            полнолуние
          </span>
          <span className="inline-flex items-center gap-1">
            <PhaseGlyph phaseIndex={2} size={9} />
            четверть
          </span>
          <span className="inline-flex items-center gap-1">
            <Info className="h-2.5 w-2.5" strokeWidth={1.75} />
            ±1 день
          </span>
        </div>
      </div>
    </section>
  )
}

/**
 * Compact SVG moon glyph for the strip. Renders the illuminated portion
 * as a simple two-tone circle — lighter than the full MoonVisual in the
 * Today widget but visually consistent.
 */
function PhaseGlyph({ phaseIndex, size = 16 }: { phaseIndex: number; size?: number }) {
  const r = size / 2
  const litColor = "oklch(0.92 0.015 85)"
  const darkColor = "oklch(0.35 0.02 295)"

  // Phase → SVG fill strategy
  if (phaseIndex === 0) {
    // New moon: all dark
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <circle cx={r} cy={r} r={r - 0.5} fill={darkColor} />
        <circle cx={r} cy={r} r={r - 0.5} fill="none" stroke="oklch(0.5 0.02 295)" strokeWidth={0.5} strokeOpacity={0.4} />
      </svg>
    )
  }
  if (phaseIndex === 4) {
    // Full moon: all lit
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <circle cx={r} cy={r} r={r - 0.5} fill={litColor} />
        {size >= 16 && (
          <>
            <circle cx={r - size * 0.15} cy={r - size * 0.1} r={size * 0.08} fill="oklch(0.82 0.015 85)" opacity={0.5} />
            <circle cx={r + size * 0.12} cy={r + size * 0.08} r={size * 0.1} fill="oklch(0.82 0.015 85)" opacity={0.4} />
          </>
        )}
      </svg>
    )
  }
  // Quarter phases: half lit
  if (phaseIndex === 2 || phaseIndex === 6) {
    const litOnRight = phaseIndex === 2 // first quarter → right lit
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <circle cx={r} cy={r} r={r - 0.5} fill={darkColor} />
        <path
          d={litOnRight
            ? `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 1 ${r} ${size - 0.5} Z`
            : `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 0 ${r} ${size - 0.5} Z`}
          fill={litColor}
        />
      </svg>
    )
  }
  // Crescent (1, 7) and gibbous (3, 5)
  const isWaxing = phaseIndex < 4
  const isCrescent = phaseIndex === 1 || phaseIndex === 7
  const illumination = phaseIndex === 1 || phaseIndex === 7 ? 25 : 75
  const terminatorRx = r * Math.abs(Math.cos((illumination / 100) * Math.PI))
  const litOnRight = isWaxing

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
      <circle cx={r} cy={r} r={r - 0.5} fill={darkColor} />
      <defs>
        <clipPath id={`strip-clip-${phaseIndex}-${size}`}>
          {isCrescent ? (
            <path
              d={`${litOnRight
                ? `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 1 ${r} ${size - 0.5}`
                : `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 0 ${r} ${size - 0.5}`} A ${terminatorRx} ${r - 0.5} 0 0 ${litOnRight ? 1 : 0} ${r} 0.5 Z`}
            />
          ) : (
            <path
              d={`${litOnRight
                ? `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 1 ${r} ${size - 0.5}`
                : `M ${r} 0.5 A ${r - 0.5} ${r - 0.5} 0 0 0 ${r} ${size - 0.5}`} A ${terminatorRx} ${r - 0.5} 0 0 ${litOnRight ? 0 : 1} ${r} 0.5 Z`}
            />
          )}
        </clipPath>
      </defs>
      <circle cx={r} cy={r} r={r - 0.5} fill={litColor} clipPath={`url(#strip-clip-${phaseIndex}-${size})`} />
    </svg>
  )
}
