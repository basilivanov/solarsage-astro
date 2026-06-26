"use client"

import { useMemo } from "react"
import { motion } from "framer-motion"
import { computeMoonPhase, getLunarDay, getVoidOfCourse } from "@/lib/moon"
import { getPlanetaryDay } from "@/lib/planetary-day"
import { getAllRetrogrades } from "@/lib/retrograde"

/**
 * DaySummaryCard — короткая обзорная сводка дня в стиле ленты.
 *
 * Формат: эмодзи + метрика → одно короткое следствие.
 * Никаких длинных текстов — только суть.
 *
 * Например:
 *   🌔 Растущая 82% → дела идут
 *   ♀ Венера управитель → день красоты и чувств
 *   ☉ Час Солнца → прояви себя
 *   🟢 Луна активна → можно начинать
 *   🟢 Все прямые → без оглядок
 */

type DayStatus = "steady" | "supportive" | "tense"

interface DaySummaryCardProps {
  date: Date
  dayStatus: DayStatus
  dominantPlanet?: string
}

const PHASE_EMOJI = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
const PHASE_NAMES = ["Новолуние", "Растущий серп", "Первая четверть", "Растущая", "Полнолуние", "Убывающая", "Последняя четв.", "Убывающий серп"]

// Короткое следствие фазы — одно предложение
const PHASE_ACTION: Record<number, string> = {
  0: "закладывай намерения",
  1: "делай первые шаги",
  2: "преодолевай препятствия",
  3: "действуй активно",
  4: "происходит кульминация",
  5: "подводи итоги",
  6: "отпускай лишнее",
  7: "отдыхай перед новым",
}

const STATUS_LINE: Record<DayStatus, { emoji: string; label: string; line: string; color: string }> = {
  steady: { emoji: "🌊", label: "Ровный день", line: "без взлётов — занимайся рутиной", color: "oklch(0.62 0.06 230)" },
  supportive: { emoji: "✨", label: "Поддерживающий", line: "день на твоей стороне — действуй", color: "oklch(0.65 0.13 145)" },
  tense: { emoji: "⚡", label: "Напряжённый", line: "не решай на эмоциях — доводи начатое", color: "oklch(0.65 0.15 27)" },
}

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}

// Короткая тема планеты в фокусе
const DOMINANT_THEME: Record<string, string> = {
  Sun: "тема дня — проявись",
  Moon: "тема дня — чувства и дом",
  Mercury: "тема дня — общение и решения",
  Venus: "тема дня — отношения и красота",
  Mars: "тема дня — действие и смелость",
  Jupiter: "тема дня — удача и масштаб",
  Saturn: "тема дня — дисциплина и итоги",
}

// Короткая тема управителя дня
const RULER_THEME: Record<string, string> = {
  Sun: "день самовыражения",
  Moon: "день чувств и дома",
  Mars: "день действия",
  Mercury: "день общения",
  Jupiter: "день удачи",
  Venus: "день красоты и чувств",
  Saturn: "день порядка",
}

// Короткая тема часа
const HOUR_THEME: Record<string, string> = {
  Sun: "проявляй себя",
  Moon: "слушай интуицию",
  Mars: "действуй быстро",
  Mercury: "звони и договаривайся",
  Jupiter: "проси масштабное",
  Venus: "время красоты и свиданий",
  Saturn: "наводи порядок",
}

export function DaySummaryCard({ date, dayStatus, dominantPlanet }: DaySummaryCardProps) {
  const moon = useMemo(() => computeMoonPhase(date), [date])
  const lunarDay = useMemo(() => getLunarDay(date), [date])
  const voc = useMemo(() => getVoidOfCourse(date), [date])
  const planetaryDay = useMemo(() => getPlanetaryDay(date), [date])
  const retrogrades = useMemo(() => getAllRetrogrades(date), [date])
  const rxCount = retrogrades.filter((r) => r.isRetrograde).length
  const rxNames = retrogrades.filter((r) => r.isRetrograde).map((r) => r.planetRu.toLowerCase())

  const status = STATUS_LINE[dayStatus] ?? STATUS_LINE.steady
  const monthNames = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

  // Собираем ленту строк
  const lines: { emoji: string; title: string; action: string; color?: string }[] = []

  // Фаза Луны
  lines.push({
    emoji: PHASE_EMOJI[moon.phaseIndex],
    title: `${PHASE_NAMES[moon.phaseIndex]} ${moon.illumination}%`,
    action: PHASE_ACTION[moon.phaseIndex],
  })

  // Лунный день — только если напряжённый или особый
  if (!lunarDay.favorable) {
    lines.push({
      emoji: "🌙",
      title: `${lunarDay.day} лунный день`,
      action: "осторожный — не начинай важное",
    })
  }

  // Управитель дня
  lines.push({
    emoji: planetaryDay.dayRulerSymbol,
    title: `${planetaryDay.dayRulerRu} управитель`,
    action: RULER_THEME[planetaryDay.dayRuler] ?? "",
    color: planetaryDay.dayRulerColor,
  })

  // Час
  lines.push({
    emoji: planetaryDay.hourRulerSymbol,
    title: `час ${planetaryDay.hourRulerRu}`,
    action: HOUR_THEME[planetaryDay.hourRuler] ?? "",
    color: planetaryDay.dayRulerColor,
  })

  // VoC
  if (voc.isVoid) {
    lines.push({
      emoji: "🟡",
      title: "Луна без курса",
      action: "не подписывай и не начинай",
    })
  }

  // Ретрограды
  if (rxCount > 0) {
    lines.push({
      emoji: "🟡",
      title: `${rxNames.join(", ")} ретроградны`,
      action: "перепроверяй и не стартуй новое в этих сферах",
    })
  }

  return (
    <section className="px-5" aria-label="Сводка дня">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/30 p-3.5"
      >
        {/* Decorative gradient */}
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 opacity-25"
          style={{
            background: `radial-gradient(circle at 85% 15%, ${status.color}18, transparent 50%), radial-gradient(circle at 15% 85%, ${planetaryDay.dayRulerColor}12, transparent 50%)`,
          }}
        />

        {/* Header: date + status */}
        <div className="relative flex items-center justify-between">
          <div className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {date.getDate()} {monthNames[date.getMonth()]} · {planetaryDay.dayOfWeekRu}
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-[13px]">{status.emoji}</span>
            <span className="text-[12px] font-medium" style={{ color: status.color }}>
              {status.label}
            </span>
          </div>
        </div>

        {/* Status one-liner */}
        <p className="relative mt-1 text-[12.5px] leading-snug text-foreground/85">
          {status.line}
        </p>

        {/* Dominant planet (если есть) */}
        {dominantPlanet && DOMINANT_THEME[dominantPlanet] && (
          <div className="relative mt-1.5 flex items-center gap-1.5 text-[12px] text-muted-foreground">
            <span className="text-[14px]" style={{ color: status.color }}>
              {PLANET_SYMBOLS[dominantPlanet]}
            </span>
            <span>{DOMINANT_THEME[dominantPlanet]}</span>
          </div>
        )}

        {/* Feed lines */}
        <div className="relative mt-2.5 space-y-1 border-t border-border/40 pt-2.5">
          {lines.map((l, i) => (
            <div key={i} className="flex items-baseline gap-2">
              <span className="text-[13px] leading-none flex-none w-5 text-center" style={l.color ? { color: l.color } : undefined}>
                {l.emoji}
              </span>
              <span className="text-[11.5px] font-medium text-foreground flex-none">
                {l.title}
              </span>
              <span className="text-[11.5px] text-muted-foreground">
                → {l.action}
              </span>
            </div>
          ))}
        </div>
      </motion.div>
    </section>
  )
}
