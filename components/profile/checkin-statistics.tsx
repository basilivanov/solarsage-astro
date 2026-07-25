// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_CHECKIN_STATISTICS
// ROLE: Checkin statistics and mood analytics section on Profile screen
// DEPENDENCIES: react, lucide-react, lib/api/checkin, packages/contracts
// GRACE_ANCHORS: [CHECKIN_STATISTICS_COMPONENT]
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT: M-COMPONENTS-CHECKIN-STATISTICS
// purpose: Render checkin statistics section with streak count, mood distribution, and tag analytics.
// owns:
//   - components/profile/checkin-statistics.tsx
// inputs: timeZone (string | null)
// outputs: CheckinStatistics React component
// dependencies: getCheckinMetrics, packages/contracts
// side_effects: fetches checkin metrics from API
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-COMPONENTS-CHECKIN-STATISTICS

// START_MODULE_MAP: M-COMPONENTS-CHECKIN-STATISTICS
// public_entrypoints:
//   - CheckinStatistics
// semantic_blocks:
//   - CHECKIN_STATISTICS_COMPONENT: checkin statistics component
// owned_tests:
//   - __tests__/components/ProfileScreen.test.tsx
// END_MODULE_MAP: M-COMPONENTS-CHECKIN-STATISTICS

"use client"

import { useEffect, useState } from "react"
import { Award, BarChart3, Calendar, Flame, TrendingUp } from "lucide-react"

import { formatDateInTimeZone, getCheckinMetrics } from "@/lib/api/checkin"
import type { CheckinMetrics } from "@/packages/contracts"

type Props = {
  timeZone?: string | null
}

const MOOD_META: Record<number, { emoji: string; color: string }> = {
  1: { emoji: "😫", color: "oklch(0.55 0.14 27)" },
  2: { emoji: "😕", color: "oklch(0.60 0.12 60)" },
  3: { emoji: "😐", color: "oklch(0.62 0.06 305)" },
  4: { emoji: "🙂", color: "oklch(0.65 0.10 150)" },
  5: { emoji: "🤩", color: "oklch(0.70 0.13 85)" },
}

const TAG_COLORS = [
  "oklch(0.62 0.06 305)",
  "oklch(0.65 0.10 150)",
  "oklch(0.70 0.13 85)",
  "oklch(0.60 0.10 230)",
  "oklch(0.58 0.14 27)",
]

function shiftDateKey(dateKey: string, days: number): string {
  const [year, month, day] = dateKey.split("-").map(Number)
  const date = new Date(Date.UTC(year, month - 1, day + days, 12))
  const shiftedYear = date.getUTCFullYear()
  const shiftedMonth = String(date.getUTCMonth() + 1).padStart(2, "0")
  const shiftedDay = String(date.getUTCDate()).padStart(2, "0")
  return `${shiftedYear}-${shiftedMonth}-${shiftedDay}`
}

// START_BLOCK: CHECKIN_STATISTICS_COMPONENT
export function CheckinStatistics({ timeZone }: Props) {
  const [metrics, setMetrics] = useState<CheckinMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const to = formatDateInTimeZone(new Date(), timeZone)
    const from = shiftDateKey(to, -29)

    setLoading(true)
    setError(null)
    getCheckinMetrics({ from, to })
      .then((value) => {
        if (!active) return
        setMetrics(value)
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(
          reason instanceof Error
            ? reason.message
            : "Не удалось загрузить статистику",
        )
        setMetrics(null)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [timeZone])

  if (loading) {
    return (
      <section className="px-5 pt-5" role="status" aria-busy="true">
        <div className="rounded-2xl border border-border/60 bg-card p-4">
          <div className="mb-4 h-3 w-36 animate-pulse rounded bg-muted" />
          <div className="grid grid-cols-2 gap-3">
            <div className="h-16 animate-pulse rounded-xl bg-muted" />
            <div className="h-16 animate-pulse rounded-xl bg-muted" />
          </div>
        </div>
      </section>
    )
  }

  if (error) {
    return (
      <section className="px-5 pt-5">
        <p className="px-1 text-[12px] text-muted-foreground" role="alert">
          Статистика оценок недоступна: {error}
        </p>
      </section>
    )
  }

  if (!metrics || metrics.totalCheckins === 0) {
    return null
  }

  const maxMoodCount = Math.max(
    ...Object.values(metrics.moodDistribution),
    1,
  )
  const topTags = Object.entries(metrics.tagFrequency)
    .sort(([, left], [, right]) => right - left)
    .slice(0, 5)
  const maxTagCount = Math.max(...topTags.map(([, count]) => count), 1)

  const stats = [
    {
      icon: Flame,
      label: "Текущая серия",
      value: `${metrics.currentStreak}`,
      suffix: "дн.",
      color: "oklch(0.58 0.14 27)",
    },
    {
      icon: Award,
      label: "Лучшая серия",
      value: `${metrics.longestStreak}`,
      suffix: "дн.",
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
      label: "Среднее",
      value: metrics.averageMood.toFixed(1),
      suffix: "/ 5",
      color: "oklch(0.65 0.10 150)",
    },
  ]

  return (
    <section className="px-5 pt-5" data-testid="profile-checkin-statistics">
      <div className="rounded-2xl border border-border/60 bg-card p-4">
        <div className="mb-3 flex items-center gap-2">
          <BarChart3
            className="h-3.5 w-3.5 text-muted-foreground"
            strokeWidth={1.75}
          />
          <h2 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Статистика оценок
          </h2>
        </div>

        <div className="grid grid-cols-2 gap-2.5">
          {stats.map((stat) => (
            <div
              key={stat.label}
              className="rounded-xl border border-border/50 bg-background/60 p-3"
            >
              <div className="flex items-center gap-1.5">
                <stat.icon
                  className="h-3.5 w-3.5"
                  style={{ color: stat.color }}
                  strokeWidth={1.75}
                />
                <span className="text-[10px] leading-tight text-muted-foreground">
                  {stat.label}
                </span>
              </div>
              <div className="mt-2 flex items-baseline gap-1">
                <span className="font-serif text-[22px] leading-none text-foreground">
                  {stat.value}
                </span>
                {stat.suffix ? (
                  <span className="text-[10px] text-muted-foreground">
                    {stat.suffix}
                  </span>
                ) : null}
              </div>
            </div>
          ))}
        </div>

        <div className="mt-5">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
              Настроение
            </span>
            <span className="text-[10px] tabular-nums text-muted-foreground">
              {metrics.totalCheckins}
            </span>
          </div>
          <div className="flex h-16 items-end gap-2">
            {[1, 2, 3, 4, 5].map((mood) => {
              const count = metrics.moodDistribution[String(mood)] ?? 0
              const meta = MOOD_META[mood]
              return (
                <div key={mood} className="flex flex-1 flex-col items-center gap-1">
                  <div className="flex h-11 w-full items-end justify-center">
                    <div
                      className="w-full max-w-7 rounded-t-md"
                      style={{
                        minHeight: count > 0 ? 4 : 2,
                        height: `${Math.max((count / maxMoodCount) * 100, count ? 8 : 2)}%`,
                        background: count ? meta.color : "oklch(0.90 0.01 295)",
                      }}
                    />
                  </div>
                  <span className="text-[10px] leading-none">{meta.emoji}</span>
                  <span className="text-[9px] tabular-nums text-muted-foreground">
                    {count}
                  </span>
                </div>
              )
            })}
          </div>
        </div>

        {topTags.length ? (
          <div className="mt-5 space-y-1.5">
            <div className="text-[10px] font-medium uppercase tracking-[0.12em] text-muted-foreground">
              Частые теги
            </div>
            {topTags.map(([tag, count], index) => (
              <div key={tag} className="flex items-center gap-2">
                <span
                  className="flex h-5 w-5 flex-none items-center justify-center rounded-md text-[9px] font-semibold"
                  style={{
                    color: TAG_COLORS[index % TAG_COLORS.length],
                    background: `${TAG_COLORS[index % TAG_COLORS.length]}14`,
                  }}
                >
                  {index + 1}
                </span>
                <span className="w-24 flex-none truncate text-[11px] text-foreground">
                  {tag}
                </span>
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(count / maxTagCount) * 100}%`,
                      background: TAG_COLORS[index % TAG_COLORS.length],
                    }}
                  />
                </div>
                <span className="w-5 text-right text-[10px] tabular-nums text-muted-foreground">
                  {count}
                </span>
              </div>
            ))}
          </div>
        ) : null}
      </div>
    </section>
  )
}
// END_BLOCK: CHECKIN_STATISTICS_COMPONENT
