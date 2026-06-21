"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Lightbulb, Sparkles, RefreshCw } from "lucide-react"
import { getLunarDay, computeMoonPhase } from "@/lib/moon"

/**
 * DayTipCard — "Совет дня" card for the Today screen.
 *
 * Generates a contextual tip based on the lunar day quality, moon phase,
 * and the day's dominant planet. The tip is actionable and specific —
 * not a generic horoscope phrase. Includes a "другой совет" cycle button.
 *
 * Tips are organized by lunar day tag (светлый/нейтральный/напряжённый/тёмный)
 * with phase-specific overrides for new/full moon days.
 */

type DayStatus = "steady" | "supportive" | "tense"

interface DayTipCardProps {
  date: Date
  /** reserved for future day-status-aware tips */
  dayStatus?: DayStatus
  /** reserved for future planet-aware tips */
  dominantPlanet?: string
}

type Tip = {
  title: string
  body: string
  category: "действие" | "рефлексия" | "отношения" | "тело" | "творчество"
}

const TIPS_BY_TAG: Record<string, Tip[]> = {
  "светлый": [
    { title: "Начни важное дело", body: "Энергия дня поддерживает начинания. Тот шаг, который ты откладывал, сегодня удастся легче всего.", category: "действие" },
    { title: "Поблагодари", body: "Напиши или скажи спасибо тому, кто недавно помог тебе. Сегодня слова благодарности имеют особый вес.", category: "отношения" },
    { title: "Создай что-то", body: "День благоприятен для творчества — рисунок, текст, музыка, кулирия. Результат удивит.", category: "творчество" },
    { title: "Выйди в люди", body: "Встреча, мероприятие, звонок — сегодня связи складываются легко. Не упусти возможность.", category: "отношения" },
  ],
  "нейтральный": [
    { title: "Структурируй день", body: "Составь список из 3 главных задач. Нейтральный день вознаграждает порядок, а не хаос.", category: "действие" },
    { title: "Прогулка без телефона", body: "20 минут на свежем воздухе без ленты. Мозг перезагрузится, и решение придёт само.", category: "тело" },
    { title: "Наведи порядок", body: "Разбери одну полку, папку или чат. Маленький порядок = большая ясность в голове.", category: "рефлексия" },
    { title: "Учись понемногу", body: "20 минут нового — книга, лекция, язык. Нейтральный день хорошо впитывает информацию.", category: "рефлексия" },
  ],
  "напряжённый": [
    { title: "Дыши перед ответом", body: "Сегодня эмоции ближе к поверхности. Прежде чем реагировать — 3 вдоха. Это спасёт разговор.", category: "рефлексия" },
    { title: "Движение снимает напряжение", body: "30 минут активности — бег, танцы, йога. Тело сбросит то, что ум не успевает переработать.", category: "тело" },
    { title: "Отложи решения", body: "Не принимай важных решений сегодня. Запиши мысли — перечитаешь завтра, увидишь иначе.", category: "рефлексия" },
    { title: "Один близкий разговор", body: "Напряжённый день смягчается теплом. Один честный разговор с тем, кому доверяешь.", category: "отношения" },
  ],
  "тёмный": [
    { title: "Тише, чем обычно", body: "День пустоты. Меньше слов, меньше планов. Позволь себе просто быть.", category: "рефлексия" },
    { title: "Сон лечит", body: "Ложись раньше. Сегодня сон восстановит вдвое больше, чем обычно.", category: "тело" },
    { title: "Не начинай нового", body: "День не для начинаний. Доделывай, отпускай, закрывай — но не открывай новое.", category: "действие" },
    { title: "Запиши сны", body: "Сны тёмного дня несут подсказки. Утром запиши, что запомнилось — позже сложится смысл.", category: "рефлексия" },
  ],
}

const PHASE_OVERRIDES: Record<number, Tip[]> = {
  0: [ // New moon
    { title: "Загадай намерение", body: "Новолуние — день закладки цикла. Напиши на бумаге одно намерение на ближайший месяц. Без свидетелей.", category: "рефлексия" },
    { title: "Тихий ритуал", body: "Зажги свечу, сделай 3 вдоха. Обозначь начало цикла. Маленький ритуал задаёт тон.", category: "рефлексия" },
  ],
  4: [ // Full moon
    { title: "Отметь кульминацию", body: "Полнолуние — пик. Подведи итог: что завершилось, что стало ясным за этот цикл?", category: "рефлексия" },
    { title: "Прояви чувства", body: "Эмоции на пике — не прячь их. Скажи то, что давно носишь. Только без обвинений.", category: "отношения" },
  ],
}

const CATEGORY_META: Record<Tip["category"], { icon: string; color: string; label: string }> = {
  "действие": { icon: "⚡", color: "oklch(0.65 0.15 27)", label: "Действие" },
  "рефлексия": { icon: "🧘", color: "oklch(0.62 0.08 230)", label: "Рефлексия" },
  "отношения": { icon: "💬", color: "oklch(0.70 0.12 15)", label: "Отношения" },
  "тело": { icon: "🌿", color: "oklch(0.65 0.13 145)", label: "Тело" },
  "творчество": { icon: "🎨", color: "oklch(0.70 0.13 85)", label: "Творчество" },
}

export function DayTipCard({ date }: DayTipCardProps) {
  const [tipIndex, setTipIndex] = useState(0)

  const tips = useMemo<Tip[]>(() => {
    const lunarDay = getLunarDay(date)
    const moon = computeMoonPhase(date)
    const base = TIPS_BY_TAG[lunarDay.tag] ?? TIPS_BY_TAG["нейтральный"]
    const overrides = PHASE_OVERRIDES[moon.phaseIndex] ?? []
    // Combine: overrides first, then base (excluding duplicates by title)
    const seen = new Set<string>()
    const combined = [...overrides, ...base].filter((t) => {
      if (seen.has(t.title)) return false
      seen.add(t.title)
      return true
    })
    return combined
  }, [date])

  // Reset index when date changes
  const tipKey = useMemo(() => `${date.toDateString()}-${tipIndex}`, [date, tipIndex])
  const tip = tips[tipIndex % tips.length]

  const lunarDay = useMemo(() => getLunarDay(date), [date])

  return (
    <section className="px-6" aria-label="Совет дня">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Совет дня
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="relative overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20">
        {/* Decorative corner glyph */}
        <span aria-hidden className="corner-glyph">✦</span>
        {/* Decorative corner glow keyed to category color */}
        <AnimatePresence mode="wait">
          <motion.div
            key={tip.category}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            aria-hidden
            className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full"
            style={{
              background: `radial-gradient(circle, ${CATEGORY_META[tip.category].color}22, transparent 70%)`,
            }}
          />
        </AnimatePresence>

        <div className="relative p-4">
          {/* Header row */}
          <div className="mb-2.5 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10">
                <Lightbulb className="h-3.5 w-3.5 text-primary" strokeWidth={1.8} />
              </span>
              <span
                className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium"
                style={{
                  color: CATEGORY_META[tip.category].color,
                  background: `${CATEGORY_META[tip.category].color}14`,
                }}
              >
                <span>{CATEGORY_META[tip.category].icon}</span>
                {CATEGORY_META[tip.category].label}
              </span>
            </div>
            <span
              className="inline-flex items-center gap-1 text-[10px] text-muted-foreground"
              title={`${lunarDay.day} лунный день · ${lunarDay.tag}`}
            >
              <Sparkles className="h-3 w-3" strokeWidth={1.8} />
              {lunarDay.tag}
            </span>
          </div>

          {/* Tip content with transition */}
          <AnimatePresence mode="wait">
            <motion.div
              key={tipKey}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.3 }}
            >
              <h3 className="font-serif text-[17px] leading-tight text-foreground">
                {tip.title}
              </h3>
              <p className="mt-1.5 text-[13px] leading-relaxed text-muted-foreground">
                {tip.body}
              </p>
            </motion.div>
          </AnimatePresence>

          {/* Footer: cycle button + counter */}
          <div className="mt-3 flex items-center justify-between border-t border-border/40 pt-2.5">
            <span className="text-[10px] tabular-nums text-muted-foreground/70">
              {tipIndex + 1} / {tips.length}
            </span>
            <button
              type="button"
              onClick={() => setTipIndex((i) => (i + 1) % tips.length)}
              className="group inline-flex items-center gap-1.5 text-[11px] font-medium text-primary transition-colors hover:text-primary/80"
            >
              <RefreshCw className="h-3 w-3 transition-transform group-hover:rotate-180 group-active:rotate-360" strokeWidth={1.8} />
              Другой совет
            </button>
          </div>
        </div>
      </div>
    </section>
  )
}
