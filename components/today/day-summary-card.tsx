"use client"

import { useMemo } from "react"
import { motion } from "framer-motion"
import { computeMoonPhase, getLunarDay, getVoidOfCourse } from "@/lib/moon"
import { getPlanetaryDay } from "@/lib/planetary-day"
import { getAllRetrogrades } from "@/lib/retrograde"

/**
 * DaySummaryCard — a concise "at a glance" summary card for the top
 * of the Today screen, combining the most important info from all
 * the individual widgets into a single scannable card.
 *
 * Shows: moon phase + illumination, lunar day, day ruler, VoC status,
 * retrograde count, and a one-line day status.
 */

type DayStatus = "steady" | "supportive" | "tense"

interface DaySummaryCardProps {
  date: Date
  dayStatus: DayStatus
  dominantPlanet?: string
}

const PHASE_EMOJI = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
const PHASE_NAMES = ["Новолуние", "Растущий серп", "Первая четверть", "Растущая", "Полнолуние", "Убывающая", "Последняя четв.", "Убывающий серп"]

const STATUS_META: Record<DayStatus, { label: string; color: string; emoji: string }> = {
  steady: { label: "Ровный день", color: "oklch(0.62 0.06 230)", emoji: "🌊" },
  supportive: { label: "Поддерживающий", color: "oklch(0.65 0.13 145)", emoji: "✨" },
  tense: { label: "Напряжённый", color: "oklch(0.65 0.15 27)", emoji: "⚡" },
}

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}
const PLANET_RU: Record<string, string> = {
  Sun: "Солнце", Moon: "Луна", Mercury: "Меркурий", Venus: "Венера",
  Mars: "Марс", Jupiter: "Юпитер", Saturn: "Сатурн",
}

export function DaySummaryCard({ date, dayStatus, dominantPlanet }: DaySummaryCardProps) {
  const moon = useMemo(() => computeMoonPhase(date), [date])
  const lunarDay = useMemo(() => getLunarDay(date), [date])
  const voc = useMemo(() => getVoidOfCourse(date), [date])
  const planetaryDay = useMemo(() => getPlanetaryDay(date), [date])
  const retrogrades = useMemo(() => getAllRetrogrades(date), [date])
  const rxCount = retrogrades.filter((r) => r.isRetrograde).length

  const statusMeta = STATUS_META[dayStatus] ?? STATUS_META.steady
  const monthNames = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

  return (
    <section className="px-5" aria-label="Сводка дня">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/30 p-4"
      >
        {/* Decorative gradient backdrop keyed to day status */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-30"
          style={{
            background: `radial-gradient(circle at 85% 15%, ${statusMeta.color}18, transparent 50%), radial-gradient(circle at 15% 85%, ${planetaryDay.dayRulerColor}12, transparent 50%)`,
          }}
        />

        {/* Date + status header */}
        <div className="relative flex items-start justify-between">
          <div>
            <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              {date.getDate()} {monthNames[date.getMonth()]} · {planetaryDay.dayOfWeekRu}
            </div>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-[16px]">{statusMeta.emoji}</span>
              <span
                className="font-serif text-[18px] leading-tight"
                style={{ color: statusMeta.color }}
              >
                {statusMeta.label}
              </span>
            </div>
          </div>
          {dominantPlanet && (
            <div className="text-right">
              <div className="text-[9px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                В фокусе
              </div>
              <div className="mt-0.5 text-[18px] leading-none" style={{ color: statusMeta.color }}>
                {PLANET_SYMBOLS[dominantPlanet] ?? "•"}
              </div>
              <div className="text-[10px] text-muted-foreground">
                {PLANET_RU[dominantPlanet] ?? ""}
              </div>
            </div>
          )}
        </div>

        {/* Key metrics grid */}
        <div className="relative mt-3 grid grid-cols-3 gap-2 border-t border-border/40 pt-3">
          {/* Moon phase */}
          <div className="text-center">
            <div className="text-[18px] leading-none">{PHASE_EMOJI[moon.phaseIndex]}</div>
            <div className="mt-1 text-[10px] font-medium text-foreground">
              {moon.illumination}%
            </div>
            <div className="text-[9px] text-muted-foreground leading-tight">
              {PHASE_NAMES[moon.phaseIndex]}
            </div>
          </div>

          {/* Lunar day */}
          <div className="text-center border-x border-border/30">
            <div
              className="text-[16px] font-bold leading-none tabular-nums"
              style={{ color: lunarDay.favorable ? "oklch(0.65 0.13 145)" : "oklch(0.65 0.15 27)" }}
            >
              {lunarDay.day}
            </div>
            <div className="mt-1 text-[9px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
              лунный день
            </div>
            <div className="text-[9px] text-muted-foreground leading-tight truncate" title={lunarDay.name}>
              {lunarDay.name.replace("День ", "")}
            </div>
          </div>

          {/* Day ruler */}
          <div className="text-center">
            <div className="text-[18px] leading-none" style={{ color: planetaryDay.dayRulerColor }}>
              {planetaryDay.dayRulerSymbol}
            </div>
            <div className="mt-1 text-[10px] font-medium text-foreground">
              {planetaryDay.dayRulerRu}
            </div>
            <div className="text-[9px] text-muted-foreground leading-tight">
              управитель
            </div>
          </div>
        </div>

        {/* Status badges row */}
        <div className="relative mt-3 flex flex-wrap items-center gap-1.5">
          {/* VoC badge */}
          {voc.isVoid ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
              Луна без курса
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-400">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              Луна активна
            </span>
          )}

          {/* Retrograde badge */}
          {rxCount > 0 ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-amber-500/15 px-2 py-0.5 text-[10px] font-medium text-amber-700 dark:text-amber-400">
              {rxCount} ретроградн.{rxCount === 1 ? "ая" : "ых"}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-700 dark:text-emerald-400">
              Все прямые
            </span>
          )}

          {/* Hour ruler badge */}
          <span
            className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
            style={{
              color: planetaryDay.dayRulerColor,
              background: `${planetaryDay.dayRulerColor}14`,
            }}
          >
            {planetaryDay.hourRulerSymbol} час {planetaryDay.hourRulerRu}
          </span>
        </div>
      </motion.div>
    </section>
  )
}
