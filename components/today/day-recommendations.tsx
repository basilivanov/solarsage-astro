"use client"

import { useMemo, useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { Check, X, ChevronRight } from "lucide-react"
import { computeMoonPhase } from "@/lib/moon"

/**
 * DayRecommendations — "Сегодня подходит для..." card.
 *
 * Generates recommended and avoided activities based on the day status
 * (steady/supportive/tense), moon phase, and the dominant planet.
 * The recommendations are deterministic per (date, status, moon) so the
 * same day always shows the same advice — but feel alive via staggered
 * entrance animations and an expandable "почему" rationale.
 */

type DayStatus = "steady" | "supportive" | "tense"

interface DayRecommendationsProps {
  date: Date
  dayStatus: DayStatus
  dominantPlanet?: string
}

type Activity = {
  label: string
  icon: string
}

type RecommendationSet = {
  goodFor: Activity[]
  avoid: Activity[]
  rationale: string
}

// ── Activity pools keyed by day status ──────────────────────────────
const BY_STATUS: Record<DayStatus, { goodFor: Activity[]; avoid: Activity[] }> = {
  steady: {
    goodFor: [
      { label: "Вести переговоры", icon: "🤝" },
      { label: "Планировать бюджет", icon: "📊" },
      { label: "Рутинные дела", icon: "📋" },
      { label: "Спокойные прогулки", icon: "🚶" },
      { label: "Чтение и учёба", icon: "📚" },
      { label: "Забота о себе", icon: "🌿" },
    ],
    avoid: [
      { label: "Резкие перемены", icon: "⚡" },
      { label: "Импульсивные траты", icon: "💸" },
      { label: "Конфронтации", icon: "🔥" },
    ],
  },
  supportive: {
    goodFor: [
      { label: "Новые знакомства", icon: "✨" },
      { label: "Свидания", icon: "💖" },
      { label: "Творческие проекты", icon: "🎨" },
      { label: "Презентации", icon: "🎤" },
      { label: "Подписание договоров", icon: "✍️" },
      { label: "Путешествия", icon: "✈️" },
    ],
    avoid: [
      { label: "Одиночество и изоляция", icon: "🌑" },
      { label: "Откладывать решения", icon: "⏳" },
      { label: "Самокритика", icon: "🪞" },
    ],
  },
  tense: {
    goodFor: [
      { label: "Физическая активность", icon: "🏃" },
      { label: "Чёткие задачи", icon: "✅" },
      { label: "Медитация", icon: "🧘" },
      { label: "Завершение дел", icon: "📦" },
      { label: "Работа с телом", icon: "💪" },
      { label: "Дневник эмоций", icon: "📝" },
    ],
    avoid: [
      { label: "Споры и ссоры", icon: "⚡" },
      { label: "Важные решения", icon: "⚠️" },
      { label: "Большие траты", icon: "💸" },
      { label: "Подписание контрактов", icon: "📜" },
    ],
  },
}

// ── Moon-phase modifiers ────────────────────────────────────────────
const MOON_MODIFIERS: Record<number, { add?: Activity[]; rationale: string }> = {
  0: {
    // New moon
    rationale: "Новолуние — время тишины и намерений. Хорошо для планирования, плохо для шума.",
    add: [{ label: "Загадывать желания", icon: "🌠" }],
  },
  2: {
    // First quarter
    rationale: "Первая четверть — время решительных действий. Препятствия преодолеваются усилием.",
  },
  4: {
    // Full moon
    rationale: "Полнолуние усиливает эмоции. Хорошо для творчества и праздников, плохо для споров.",
    add: [{ label: "Творческие ритуалы", icon: "🌙" }],
  },
  6: {
    // Last quarter
    rationale: "Последняя четверть — время освобождения и подведения итогов.",
    add: [{ label: "Расхламление", icon: "🧹" }],
  },
}

const PHASE_RATIONALES = [
  "Новолуние — закладка намерений на цикл.",
  "Растущий серп — первые шаги к намеченной цели.",
  "Первая четверть — проверка решимости и действий.",
  "Растущая Луна — накопление энергии перед пиком.",
  "Полнолуние — кульминация, эмоциональная ясность.",
  "Убывающая Луна — благодарность и распределение.",
  "Последняя четверть — пересмотр и освобождение.",
  "Убывающий серп — тишина, рефлексия, закрытие цикла.",
]

const PLANET_RATIONALE: Record<string, string> = {
  Sun: "Солнце в фокусе — день личной силы и самовыражения.",
  Moon: "Луна ведёт день — слушай эмоции и интуицию.",
  Mercury: "Меркурий активен — день для слов, переговоров, документов.",
  Venus: "Венера ведёт — день любви, красоты, партнёрства.",
  Mars: "Марс разгорячен — действуй, но следи за гневом.",
  Jupiter: "Юпитер расширяет — удача, рост, щедрость.",
  Saturn: "Сатурн структурирует — дисциплина и ответственность.",
  Uranus: "Уран будоражит — неожиданности и озарения.",
  Neptune: "Нептун смягчает — воображение, творчество, но и иллюзии.",
  Pluto: "Плутон трансформирует — глубинные перемены.",
}

export function DayRecommendations({ date, dayStatus, dominantPlanet }: DayRecommendationsProps) {
  const [expanded, setExpanded] = useState(false)

  const { goodFor, avoid, rationale } = useMemo<RecommendationSet>(() => {
    const moon = computeMoonPhase(date)
    const base = BY_STATUS[dayStatus] ?? BY_STATUS.steady
    const modifier = MOON_MODIFIERS[moon.phaseIndex]

    // Deterministic pick: use date + moon phase to select 4 "good" + 2 "avoid"
    const seed = Math.floor(date.getTime() / 86400000) + moon.phaseIndex * 7
    const goodPool = [...base.goodFor, ...(modifier?.add ?? [])]
    const goodFor = pickDeterministic(goodPool, 4, seed)
    const avoid = pickDeterministic(base.avoid, 2, seed + 1)

    const rationale = [
      modifier?.rationale ?? PHASE_RATIONALES[moon.phaseIndex],
      PLANET_RATIONALE[dominantPlanet ?? ""],
    ]
      .filter(Boolean)
      .join(" ")

    return { goodFor, avoid, rationale }
  }, [date, dayStatus, dominantPlanet])

  const statusLabel =
    dayStatus === "supportive" ? "поддерживающий" : dayStatus === "tense" ? "напряжённый" : "ровный"

  return (
    <section className="px-6" aria-label="Сегодня подходит для">
      <div className="mb-3 flex items-center gap-3">
        <span className="h-px flex-1 bg-border" />
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Сегодня подходит для
        </span>
        <span className="h-px flex-1 bg-border" />
      </div>

      <div className="overflow-hidden rounded-2xl border border-border/60 bg-gradient-to-br from-card via-card to-secondary/20">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-border/50 px-4 py-3">
          <div className="flex items-center gap-2">
            <span className="relative flex h-2 w-2">
              <span
                className={`pulse-dot-soft absolute inline-flex h-full w-full rounded-full ${
                  dayStatus === "tense"
                    ? "bg-amber-500/60"
                    : dayStatus === "supportive"
                      ? "bg-emerald-500/60"
                      : "bg-primary/60"
                }`}
              />
              <span
                className={`relative inline-flex h-2 w-2 rounded-full ${
                  dayStatus === "tense"
                    ? "bg-amber-500"
                    : dayStatus === "supportive"
                      ? "bg-emerald-500"
                      : "bg-primary"
                }`}
              />
            </span>
            <span className="text-[12px] font-medium text-foreground">
              День — <span className="text-primary/90">{statusLabel}</span>
            </span>
          </div>
          <button
            type="button"
            onClick={() => setExpanded((v) => !v)}
            className="flex items-center gap-0.5 text-[11px] text-muted-foreground transition-colors hover:text-foreground"
            aria-expanded={expanded}
          >
            {expanded ? "скрыть" : "почему"}
            <ChevronRight
              className={`h-3 w-3 transition-transform ${expanded ? "rotate-90" : ""}`}
              strokeWidth={2}
            />
          </button>
        </div>

        {/* Two columns: good for / avoid */}
        <div className="grid grid-cols-1 gap-0 sm:grid-cols-2">
          {/* Good for */}
          <div className="border-b border-border/40 px-4 py-3 sm:border-b-0 sm:border-r">
            <div className="mb-2 flex items-center gap-1.5">
              <span className="flex h-4 w-4 items-center justify-center rounded-full bg-emerald-500/15">
                <Check className="h-2.5 w-2.5 text-emerald-600 dark:text-emerald-400" strokeWidth={3} />
              </span>
              <span className="text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                Хорошо
              </span>
            </div>
            <ul className="space-y-1.5">
              {goodFor.map((a, i) => (
                <motion.li
                  key={a.label}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06, duration: 0.3 }}
                  className="flex items-center gap-2 text-[12.5px] text-foreground/90"
                >
                  <span className="text-[14px] leading-none">{a.icon}</span>
                  <span>{a.label}</span>
                </motion.li>
              ))}
            </ul>
          </div>

          {/* Avoid */}
          <div className="px-4 py-3">
            <div className="mb-2 flex items-center gap-1.5">
              <span className="flex h-4 w-4 items-center justify-center rounded-full bg-amber-500/15">
                <X className="h-2.5 w-2.5 text-amber-600 dark:text-amber-400" strokeWidth={3} />
              </span>
              <span className="text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                Лучше избегать
              </span>
            </div>
            <ul className="space-y-1.5">
              {avoid.map((a, i) => (
                <motion.li
                  key={a.label}
                  initial={{ opacity: 0, x: 6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.24 + i * 0.06, duration: 0.3 }}
                  className="flex items-center gap-2 text-[12.5px] text-muted-foreground"
                >
                  <span className="text-[14px] leading-none opacity-70">{a.icon}</span>
                  <span className="line-through decoration-muted-foreground/30 decoration-1">
                    {a.label}
                  </span>
                </motion.li>
              ))}
            </ul>
          </div>
        </div>

        {/* Expandable rationale */}
        <AnimatePresence initial={false}>
          {expanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25 }}
              className="overflow-hidden"
            >
              <div className="border-t border-border/40 bg-secondary/20 px-4 py-3">
                <div className="mb-1 text-[10px] font-medium uppercase tracking-[0.1em] text-muted-foreground">
                  Почему так
                </div>
                <p className="text-[12px] leading-relaxed text-foreground/80">{rationale}</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </section>
  )
}

/**
 * Deterministic pick of `count` items from `pool` using a seed.
 * Same seed → same selection (stable per day).
 */
function pickDeterministic<T>(pool: T[], count: number, seed: number): T[] {
  if (pool.length <= count) return [...pool]
  const result: T[] = []
  const used = new Set<number>()
  let s = seed
  while (result.length < count && used.size < pool.length) {
    s = (s * 9301 + 49297) % 233280
    const idx = Math.floor((s / 233280) * pool.length)
    if (!used.has(idx)) {
      used.add(idx)
      result.push(pool[idx])
    }
  }
  return result
}
