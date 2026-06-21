"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Sparkles, RefreshCw, Heart } from "lucide-react"

/**
 * DailyAffirmation — a small card showing a daily affirmation/insight
 * derived from the day's dominant planet and aspects. Users can cycle
 * through alternative affirmations.
 *
 * Purely client-side derivation from the day status + a deterministic
 * seed based on the date so the same day always shows the same primary
 * affirmation.
 */

interface DailyAffirmationProps {
  date: Date
  dayStatus: "steady" | "supportive" | "tense"
  dominantPlanet?: string
}

interface Affirmation {
  text: string
  planet: string
  tone: "calm" | "active" | "reflective"
}

const AFFIRMATIONS: Record<string, Affirmation[]> = {
  steady: [
    { text: "Сегодня я нахожу опору в спокойствии и ясности. Каждый шаг осознан.", planet: "Moon", tone: "calm" },
    { text: "Я доверяю ритму дня и позволяю событиям развиваться естественно.", planet: "Sun", tone: "calm" },
    { text: "Мой внутренний баланс — моя сила. Я остаюсь центрированным.", planet: "Saturn", tone: "reflective" },
    { text: "Сегодня я выбираю присутствие. Я здесь, сейчас, полностью.", planet: "Mercury", tone: "reflective" },
  ],
  supportive: [
    { text: "Я открыт потоку удачи и возможностей. Сегодня всё складывается для меня.", planet: "Jupiter", tone: "active" },
    { text: "Моя энергия направлена на рост и созидание. Я приветствую новое.", planet: "Venus", tone: "active" },
    { text: "Я заслуживаю радости и тепла. Сегодня я позволяю себе наслаждаться.", planet: "Venus", tone: "calm" },
    { text: "Мои действия сегодня наполнены смыслом и приводят к результату.", planet: "Mars", tone: "active" },
  ],
  tense: [
    { text: "Я выбираю мир внутри себя, что бы ни происходило снаружи.", planet: "Moon", tone: "calm" },
    { text: "Напряжение дня проходит через меня, не задевая моего центра.", planet: "Saturn", tone: "reflective" },
    { text: "Я дышу медленно и действую осознанно. Я не реагирую — я выбираю.", planet: "Mercury", tone: "reflective" },
    { text: "Сегодняшние вызовы делают меня сильнее. Я справляюсь.", planet: "Mars", tone: "active" },
  ],
}

const TONE_STYLES: Record<string, { color: string; bg: string; icon: typeof Heart }> = {
  calm: {
    color: "oklch(0.65 0.10 150)",
    bg: "oklch(0.65 0.10 150 / 0.08)",
    icon: Heart,
  },
  active: {
    color: "oklch(0.70 0.13 85)",
    bg: "oklch(0.70 0.13 85 / 0.08)",
    icon: Sparkles,
  },
  reflective: {
    color: "oklch(0.62 0.06 305)",
    bg: "oklch(0.62 0.06 305 / 0.08)",
    icon: RefreshCw,
  },
}

function dateSeed(date: Date): number {
  return Math.floor(date.getTime() / (1000 * 60 * 60 * 24))
}

export function DailyAffirmation({ date, dayStatus, dominantPlanet }: DailyAffirmationProps) {
  const seed = dateSeed(date)
  const baseIndex = seed % AFFIRMATIONS[dayStatus].length
  const [offset, setOffset] = useState(0)

  const current = useMemo(() => {
    const list = AFFIRMATIONS[dayStatus]
    const idx = (baseIndex + offset) % list.length
    return list[idx]
  }, [baseIndex, offset, dayStatus])

  const tone = TONE_STYLES[current.tone]
  const ToneIcon = tone.icon

  const cycle = () => {
    setOffset((o) => o + 1)
  }

  return (
    <section className="px-6" aria-label="Аффирмация дня">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
        className="relative overflow-hidden rounded-2xl border p-4"
        style={{
          borderColor: `${tone.color}30`,
          background: `linear-gradient(135deg, ${tone.bg}, transparent 70%)`,
        }}
      >
        {/* decorative corner glow */}
        <div
          aria-hidden
          className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-40"
          style={{
            background: `radial-gradient(circle, ${tone.color}40, transparent 70%)`,
          }}
        />

        <div className="relative flex items-start gap-3">
          <div
            className="flex h-9 w-9 flex-none items-center justify-center rounded-full"
            style={{ background: tone.bg, color: tone.color }}
          >
            <Sparkles className="h-4 w-4" strokeWidth={1.75} />
          </div>

          <div className="min-w-0 flex-1">
            <div className="mb-1.5 flex items-center gap-2">
              <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
                Аффирмация дня
              </span>
              <span
                className="inline-flex items-center gap-0.5 rounded-full px-1.5 py-0.5 text-[9px] font-medium"
                style={{ background: tone.bg, color: tone.color }}
              >
                <ToneIcon className="h-2.5 w-2.5" strokeWidth={2} />
                {current.tone === "calm" ? "спокойствие" : current.tone === "active" ? "действие" : "рефлексия"}
              </span>
            </div>

            <AnimatePresence mode="wait">
              <motion.p
                key={offset}
                initial={{ opacity: 0, x: 10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.25 }}
                className="font-serif text-[17px] leading-snug text-foreground"
              >
                {current.text}
              </motion.p>
            </AnimatePresence>

            <div className="mt-3 flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground">
                {dominantPlanet ? `через ${dominantPlanet}` : ""}
              </span>
              <button
                type="button"
                onClick={cycle}
                className="inline-flex items-center gap-1 rounded-full border border-border/50 bg-card/60 px-2.5 py-1 text-[10px] font-medium text-muted-foreground transition hover:text-foreground active:scale-95"
              >
                <RefreshCw className="h-2.5 w-2.5" strokeWidth={2} />
                другая
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  )
}
