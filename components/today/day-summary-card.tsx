"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ChevronDown, Info } from "lucide-react"
import { computeMoonPhase, getLunarDay, getVoidOfCourse } from "@/lib/moon"
import { getPlanetaryDay } from "@/lib/planetary-day"
import { getAllRetrogrades } from "@/lib/retrograde"

/**
 * DaySummaryCard — сводка дня с интерпретацией.
 *
 * Каждый показатель сопровождается короткой подсказкой «что это значит
 * для тебя сегодня» — чтобы человек не видел сухие факты, а понимал,
 * как их использовать.
 */

type DayStatus = "steady" | "supportive" | "tense"

interface DaySummaryCardProps {
  date: Date
  dayStatus: DayStatus
  dominantPlanet?: string
}

const PHASE_EMOJI = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"]
const PHASE_NAMES = ["Новолуние", "Растущий серп", "Первая четверть", "Растущая", "Полнолуние", "Убывающая", "Последняя четв.", "Убывающий серп"]

const PHASE_HINTS: Record<number, string> = {
  0: "Время закладывать намерения. Не начинай сразу — помечтай, что хочешь на этот цикл",
  1: "Первые шаги к цели. Действуй осторожно, проверяя направление",
  2: "Решительный момент. Препятствия преодолеваются усилием",
  3: "Энергия нарастает. Хороший период для активных дел",
  4: "Пик эмоций. Ясность, кульминация. Не принимай решений на пике чувств",
  5: "Подведение итогов. Благодарность, распределение, завершение",
  6: "Пересмотр и освобождение. Отпусти то, что больше не работает",
  7: "Тишина и рефлексия. Закрытие цикла, отдых перед новым",
}

const STATUS_META: Record<DayStatus, { label: string; color: string; emoji: string; hint: string }> = {
  steady: {
    label: "Ровный день",
    color: "oklch(0.62 0.06 230)",
    emoji: "🌊",
    hint: "Энергия стабильна. Без взлётов и падений — хорошо для рутины, планирования, обычных дел. Резких перемен лучше избегать",
  },
  supportive: {
    label: "Поддерживающий",
    color: "oklch(0.65 0.13 145)",
    emoji: "✨",
    hint: "День на твоей стороне. Начинания, знакомства, важные разговоры удаются легче. Проси — дадут, действуй — получится",
  },
  tense: {
    label: "Напряжённый",
    color: "oklch(0.65 0.15 27)",
    emoji: "⚡",
    hint: "Энергия рваная. Не принимай решений на эмоциях, избегай конфликтов. Лучше доводи начатое, чем начинай новое",
  },
}

const PLANET_SYMBOLS: Record<string, string> = {
  Sun: "☉", Moon: "☽", Mercury: "☿", Venus: "♀", Mars: "♂",
  Jupiter: "♃", Saturn: "♄", Uranus: "♅", Neptune: "♆", Pluto: "♇",
}
const PLANET_RU: Record<string, string> = {
  Sun: "Солнце", Moon: "Луна", Mercury: "Меркурий", Venus: "Венера",
  Mars: "Марс", Jupiter: "Юпитер", Saturn: "Сатурн",
}

const DOMINANT_PLANET_HINT: Record<string, string> = {
  Sun: "Тема дня — ты. Самовыражение, лидерство, проявись. Хорошо для публичности и творчества",
  Moon: "Тема дня — чувства. Слушай интуицию, заботься о себе и близких. Дом и семья в фокусе",
  Mercury: "Тема дня — общение. Переговоры, документы, учёба. Слова сегодня убедительны",
  Venus: "Тема дня — отношения и красота. Свидания, искусство, покупки. Проси поддержки",
  Mars: "Тема дня — действие. Спорт, инициатива, смелость. Энергия бьёт — направь её",
  Jupiter: "Тема дня — расширение. Удача, рост, масштаб. Хорошо для крупных начинаний",
  Saturn: "Тема дня — дисциплина. Порядок, ответственность, итоги. Не торопись — доводи",
}

const DAY_RULER_HINT: Record<string, string> = {
  Sun: "День самовыражения и творчества. Проявись, будь щедрым, ищи признания",
  Moon: "День эмоций и дома. Заботься, отдыхай, наводи порядок в чувствах",
  Mars: "День действия и смелости. Спорт, инициатива, решение сложных задач",
  Mercury: "День общения и учёбы. Переговоры, документы, обучение",
  Jupiter: "День удачи и мудрости. Крупные начинания, путешествия, обучение",
  Venus: "День любви и красоты. Свидания, искусство, покупки, примирение",
  Saturn: "День дисциплины и итогов. Уборка, планирование, рутинные дела",
}

const HOUR_RULER_HINT: Record<string, string> = {
  Sun: "Час активности. Хорошо для публичных дел и проявления себя",
  Moon: "Час эмоций. Слушай интуицию, хорошо для заботы и домашних дел",
  Mars: "Час действия. Быстрые решения, спорт, смелость",
  Mercury: "Час общения. Звонки, письма, переговоры, учёба",
  Jupiter: "Час удачи. Масштабные шаги, подарки, крупные просьбы",
  Venus: "Час красоты. Свидания, творчество, покупки, примирение",
  Saturn: "Час порядка. Планирование, дисциплина, завершение дел",
}

export function DaySummaryCard({ date, dayStatus, dominantPlanet }: DaySummaryCardProps) {
  const [expanded, setExpanded] = useState(false)

  const moon = useMemo(() => computeMoonPhase(date), [date])
  const lunarDay = useMemo(() => getLunarDay(date), [date])
  const voc = useMemo(() => getVoidOfCourse(date), [date])
  const planetaryDay = useMemo(() => getPlanetaryDay(date), [date])
  const retrogrades = useMemo(() => getAllRetrogrades(date), [date])
  const rxCount = retrogrades.filter((r) => r.isRetrograde).length
  const rxNames = retrogrades.filter((r) => r.isRetrograde).map((r) => r.planetRu).join(", ")

  const statusMeta = STATUS_META[dayStatus] ?? STATUS_META.steady
  const monthNames = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]

  const lunarDayHint = lunarDay.favorable
    ? `Благоприятный день. ${lunarDay.description}`
    : `Осторожный день. ${lunarDay.description}`

  const vocHint = voc.isVoid
    ? "Луна без курса — не начинай новое, не подписывай важное. Доводи начатое, отдыхай"
    : "Луна активна — можно начинать дела, принимать решения, подписывать"

  const rxHint = rxCount > 0
    ? `${rxNames} ретроградны. Перепроверяй ${retrogrades.find(r => r.planet === "Mercury")?.isRetrograde ? "документы и факты" : ""}${retrogrades.find(r => r.planet === "Venus")?.isRetrograde ? " отношения" : ""}${retrogrades.find(r => r.planet === "Mars")?.isRetrograde ? " физические решения" : ""}. Не стартуй новое в этих сферах`
    : "Все планеты прямые — можно начинать новое, подписывать, принимать решения без оглядок"

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
          <div className="flex-1 min-w-0">
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
            <p className="mt-1 text-[11.5px] leading-snug text-muted-foreground">
              {statusMeta.hint}
            </p>
          </div>
          {dominantPlanet && (
            <div className="text-right flex-none ml-2">
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

        {/* Dominant planet hint */}
        {dominantPlanet && DOMINANT_PLANET_HINT[dominantPlanet] && (
          <div className="relative mt-2 rounded-lg bg-secondary/30 px-3 py-1.5 text-[11px] leading-snug text-foreground/80">
            {DOMINANT_PLANET_HINT[dominantPlanet]}
          </div>
        )}

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

        {/* Interpretation hints */}
        <div className="relative mt-3 space-y-1.5">
          {/* Moon phase interpretation */}
          <HintRow emoji={PHASE_EMOJI[moon.phaseIndex]} label={PHASE_NAMES[moon.phaseIndex]} hint={PHASE_HINTS[moon.phaseIndex]} />

          {/* Lunar day interpretation */}
          <HintRow
            emoji={lunarDay.favorable ? "✅" : "⚠️"}
            label={`${lunarDay.day} лунный день`}
            hint={lunarDayHint}
          />

          {/* Day ruler interpretation */}
          <HintRow
            emoji={planetaryDay.dayRulerSymbol}
            label={`${planetaryDay.dayRulerRu} — управитель дня`}
            hint={DAY_RULER_HINT[planetaryDay.dayRuler] ?? ""}
            color={planetaryDay.dayRulerColor}
          />

          {/* Hour ruler interpretation */}
          <HintRow
            emoji={planetaryDay.hourRulerSymbol}
            label={`Час ${planetaryDay.hourRulerRu}`}
            hint={HOUR_RULER_HINT[planetaryDay.hourRuler] ?? ""}
            color={planetaryDay.dayRulerColor}
          />
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

        {/* Expandable: VoC + retrograde interpretations */}
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="relative mt-2 flex w-full items-center justify-center gap-1 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
        >
          <Info className="h-3 w-3" strokeWidth={1.8} />
          {expanded ? "скрыть детали" : "что это значит?"}
          <ChevronDown
            className={`h-3 w-3 transition-transform ${expanded ? "rotate-180" : ""}`}
            strokeWidth={1.8}
          />
        </button>

        <AnimatePresence initial={false}>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="relative mt-2 space-y-2 border-t border-border/40 pt-3">
                {/* VoC interpretation */}
                <div className="rounded-lg bg-secondary/30 px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <span className={`h-2 w-2 rounded-full ${voc.isVoid ? "bg-amber-500" : "bg-emerald-500"}`} />
                    <span className="text-[11px] font-medium text-foreground">
                      {voc.isVoid ? "Луна без курса" : "Луна активна"}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                    {vocHint}
                  </p>
                </div>

                {/* Retrograde interpretation */}
                <div className="rounded-lg bg-secondary/30 px-3 py-2">
                  <div className="flex items-center gap-1.5">
                    <span className={`h-2 w-2 rounded-full ${rxCount > 0 ? "bg-amber-500" : "bg-emerald-500"}`} />
                    <span className="text-[11px] font-medium text-foreground">
                      {rxCount > 0 ? `${rxNames} ретроградны` : "Все планеты прямые"}
                    </span>
                  </div>
                  <p className="mt-1 text-[11px] leading-relaxed text-muted-foreground">
                    {rxHint}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </section>
  )
}

function HintRow({ emoji, label, hint, color }: { emoji: string; label: string; hint: string; color?: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-background/40 px-2.5 py-1.5">
      <span className="text-[13px] leading-none mt-0.5 flex-none" style={color ? { color } : undefined}>
        {emoji}
      </span>
      <div className="min-w-0 flex-1">
        <span className="text-[11px] font-medium text-foreground">{label}</span>
        <span className="text-[11px] text-muted-foreground"> — {hint}</span>
      </div>
    </div>
  )
}
