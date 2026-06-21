"use client"

import { useEffect, useState } from "react"
import { motion } from "framer-motion"
import { Flame, TrendingUp, Calendar, Award, BarChart3 } from "lucide-react"

/**
 * CheckinStatistics — visual summary of the user's evening check-in
 * history. Fetches from /api/checkin/metrics (mock returns demo data).
 *
 * Shows: current streak, longest streak, average mood, total checkins,
 * mood distribution bar chart, and top tags.
 */

interface CheckinMetrics {
  totalCheckins: number
  currentStreak: number
  longestStreak: number
  averageMood: number
  averageAccuracy: number
  moodDistribution: Record<number, number>
  tagFrequency: Record<string, number>
}

const DEFAULT_METRICS: CheckinMetrics = {
  totalCheckins: 0,
  currentStreak: 0,
  longestStreak: 0,
  averageMood: 0,
  averageAccuracy: 0,
  moodDistribution: {},
  tagFrequency: {},
}

const MOOD_LABELS: Record<number, { label: string; emoji: string; color: string }> = {
  1: { label: "Тяжелый", emoji: "😞", color: "oklch(0.55 0.14 27)" },
  2: { label: "Сложный", emoji: "😕", color: "oklch(0.60 0.12 60)" },
  3: { label: "Обычный", emoji: "😐", color: "oklch(0.62 0.06 305)" },
  4: { label: "Хороший", emoji: "🙂", color: "oklch(0.65 0.10 150)" },
  5: { label: "Отличный", emoji: "😄", color: "oklch(0.70 0.13 85)" },
}

const TAG_COLORS = [
  "oklch(0.62 0.06 305)",
  "oklch(0.65 0.10 150)",
  "oklch(0.70 0.13 85)",
  "oklch(0.60 0.10 230)",
  "oklch(0.58 0.14 27)",
  "oklch(0.68 0.10 200)",
]

export function CheckinStatistics() {
  const [metrics, setMetrics] = useState<CheckinMetrics>(DEFAULT_METRICS)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const today = new Date()
    const from = new Date(today)
    from.setDate(from.getDate() - 30)
    const fromStr = from.toISOString().split("T")[0]
    const toStr = today.toISOString().split("T")[0]

    fetch(`/api/checkin/metrics?from=${fromStr}&to=${toStr}`, { credentials: "include" })
      .then((r) => (r.ok ? r.json() : DEFAULT_METRICS))
      .then((data) => setMetrics({ ...DEFAULT_METRICS, ...data }))
      .catch(() => setMetrics(DEFAULT_METRICS))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <section className="px-5 pt-5">
        <div className="animate-pulse rounded-2xl border border-border/50 bg-card p-4">
          <div className="mb-3 h-3 w-32 rounded bg-muted" />
          <div className="grid grid-cols-2 gap-3">
            <div className="h-16 rounded-lg bg-muted" />
            <div className="h-16 rounded-lg bg-muted" />
          </div>
        </div>
      </section>
    )
  }

  if (metrics.totalCheckins === 0) {
    return null
  }

  const maxMoodCount = Math.max(...Object.values(metrics.moodDistribution), 1)
  const sortedTags = Object.entries(metrics.tagFrequency)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)
  const maxTagCount = Math.max(...sortedTags.map(([, c]) => c), 1)

  const stats = [
    {
      icon: Flame,
      label: "Текущая серия",
      value: `${metrics.currentStreak}`,
      suffix: metrics.currentStreak === 1 ? "день" : metrics.currentStreak < 5 ? "дня" : "дней",
      color: "oklch(0.58 0.14 27)",
      highlight: metrics.currentStreak >= 3,
    },
    {
      icon: Award,
      label: "Лучшая серия",
      value: `${metrics.longestStreak}`,
      suffix: "дней",
      color: "oklch(0.70 0.13 85)",
    },
    {
      icon: Calendar,
      label: "Всего оценок",
      value: `${metrics.totalCheckins}`,
      suffix: "",
      color: "oklch(0.62 0.06 305)",
    },
    {
      icon: TrendingUp,
      label: "Среднее настроение",
      value: metrics.averageMood.toFixed(1),
      suffix: "/ 5",
      color: "oklch(0.65 0.10 150)",
    },
  ]

  return (
    <section className="px-5 pt-5">
      <div className="rounded-2xl border border-border/50 bg-gradient-to-br from-card via-card to-secondary/20 p-4">
        <div className="mb-3 flex items-center gap-2">
          <BarChart3 className="h-3.5 w-3.5 text-muted-foreground" strokeWidth={1.75} />
          <h2 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Статистика оценок
          </h2>
        </div>

        {/* Stat grid */}
        <div className="mb-4 grid grid-cols-2 gap-2.5">
          {stats.map((s, i) => (
            <motion.div
              key={s.label}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.3, delay: i * 0.08 }}
              className="relative overflow-hidden rounded-xl border border-border/40 bg-background/60 p-3"
            >
              <div className="flex items-center gap-1.5">
                <s.icon
                  className="h-3 w-3 flex-none"
                  style={{ color: s.color }}
                  strokeWidth={2}
                />
                <span className="text-[10px] leading-tight text-muted-foreground">
                  {s.label}
                </span>
              </div>
              <div className="mt-1.5 flex items-baseline gap-1">
                <span
                  className="font-serif text-[22px] leading-none"
                  style={{ color: s.highlight ? s.color : "var(--foreground)" }}
                >
                  {s.value}
                </span>
                {s.suffix && (
                  <span className="text-[10px] text-muted-foreground">{s.suffix}</span>
                )}
                {s.highlight && (
                  <span className="ml-0.5 text-xs">🔥</span>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Mood distribution */}
        <div className="mb-4">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
              Распределение настроения
            </span>
            <span className="text-[10px] tabular-nums text-muted-foreground/70">
              {metrics.totalCheckins} оценок
            </span>
          </div>
          <div className="flex h-16 items-end justify-between gap-1.5">
            {[1, 2, 3, 4, 5].map((mood) => {
              const count = metrics.moodDistribution[mood] ?? 0
              const heightPct = (count / maxMoodCount) * 100
              const cfg = MOOD_LABELS[mood]
              return (
                <div key={mood} className="flex flex-1 flex-col items-center gap-1">
                  <div className="flex h-12 w-full items-end justify-center">
                    <motion.div
                      initial={{ height: 0 }}
                      animate={{ height: `${Math.max(heightPct, count > 0 ? 8 : 2)}%` }}
                      transition={{ duration: 0.5, delay: 0.2 + mood * 0.08, ease: "easeOut" }}
                      className="w-full max-w-[28px] rounded-t-md"
                      style={{
                        background: count > 0
                          ? `linear-gradient(180deg, ${cfg.color}, ${cfg.color}cc)`
                          : "oklch(0.90 0.01 295)",
                        minHeight: count > 0 ? 4 : 2,
                      }}
                      title={`${cfg.label}: ${count}`}
                    />
                  </div>
                  <span className="text-[10px] leading-none">{cfg.emoji}</span>
                  <span className="text-[9px] tabular-nums text-muted-foreground">
                    {count}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {/* Top tags */}
        {sortedTags.length > 0 && (
          <div>
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
                Частые теги
              </span>
            </div>
            <div className="space-y-1.5">
              {sortedTags.map(([tag, count], i) => (
                <motion.div
                  key={tag}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.3, delay: 0.3 + i * 0.05 }}
                  className="flex items-center gap-2"
                >
                  <span
                    className="flex h-5 w-5 flex-none items-center justify-center rounded-md text-[9px] font-semibold"
                    style={{
                      color: TAG_COLORS[i % TAG_COLORS.length],
                      background: `${TAG_COLORS[i % TAG_COLORS.length]}14`,
                    }}
                  >
                    {i + 1}
                  </span>
                  <span className="w-24 flex-none text-[11px] font-medium text-foreground truncate">
                    {tag}
                  </span>
                  <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${(count / maxTagCount) * 100}%` }}
                      transition={{ duration: 0.6, delay: 0.35 + i * 0.05, ease: "easeOut" }}
                      className="absolute inset-y-0 left-0 rounded-full"
                      style={{ background: TAG_COLORS[i % TAG_COLORS.length] }}
                    />
                  </div>
                  <span className="w-5 flex-none text-right text-[10px] tabular-nums text-muted-foreground">
                    {count}
                  </span>
                </motion.div>
              ))}
            </div>
          </div>
        )}

        <p className="mt-3 border-t border-border/30 pt-2 text-center text-[10px] text-muted-foreground/70">
          За последние 30 дней · данные демо-режима
        </p>
      </div>
    </section>
  )
}
