// ############################################################################
// AI_HEADER: MODULE_PROFILE_CHECKIN_STATS_CARD
// ROLE: UI component for checkin statistics and streak gamification badges in Profile
// DEPENDENCIES: react, lucide-react, lib/api/checkin, packages/contracts
// ############################################################################

// START_MODULE_CONTRACT: M-PROFILE-CHECKIN-STATS-CARD
// purpose: Render checkin streak metrics, total count, and milestone badges (3/7/14/30 days) on Profile screen.
// owns:
//   - components/profile/checkin-stats-card.tsx
// inputs: timeZone (optional)
// outputs: CheckinStatsCard React component
// dependencies: lib/api/checkin, packages/contracts
// side_effects: fetches checkin metrics on mount
// emitted_logs: none
// failure_policy: fails open (renders quiet state on error)
// END_MODULE_CONTRACT: M-PROFILE-CHECKIN-STATS-CARD

// START_MODULE_MAP: M-PROFILE-CHECKIN-STATS-CARD
// public_entrypoints:
//   - CheckinStatsCard
// semantic_blocks:
//   - CHECKIN_STATS_CARD_COMPONENT: streak metrics & milestones component
// owned_tests:
//   - __tests__/components/CheckinStatsCard.test.tsx
// END_MODULE_MAP: M-PROFILE-CHECKIN-STATS-CARD

"use client"

import { useEffect, useState } from "react"
import { Flame, Award } from "lucide-react"
import { getCheckinMetrics } from "@/lib/api/checkin"
import type { CheckinMetrics } from "@/packages/contracts"

const MILESTONES = [
  { days: 3, label: "3 дня" },
  { days: 7, label: "Неделя" },
  { days: 14, label: "2 недели" },
  { days: 30, label: "Месяц" },
]

// START_BLOCK: CHECKIN_STATS_CARD_COMPONENT
export function CheckinStatsCard() {
  const [metrics, setMetrics] = useState<CheckinMetrics | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let active = true
    getCheckinMetrics()
      .then((res) => {
        if (active) setMetrics(res)
      })
      .catch(() => {
        /* fail open */
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [])

  if (loading) {
    return (
      <div className="rounded-2xl border border-border/70 bg-card p-5 text-[13px] text-muted-foreground">
        Загружаем статистику чекинов…
      </div>
    )
  }

  const streak = metrics?.currentStreak ?? 0
  const longest = metrics?.longestStreak ?? 0
  const total = metrics?.totalCheckins ?? 0

  return (
    <div className="rounded-2xl border border-border/70 bg-card p-5 space-y-4" data-testid="checkin-stats-card">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#fbf1de] text-[#b07b36] dark:bg-[#2d261a] dark:text-[#d49a4f]">
            <Flame className="h-5 w-5" />
          </div>
          <div>
            <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground block">
              СЕРИЯ ДНЕЙ
            </span>
            <h3 className="font-serif text-[18px] font-semibold text-foreground m-0 leading-tight">
              {streak > 0 ? `🔥 ${streak} ${pluralDays(streak)} подряд` : "Начни новую серию"}
            </h3>
          </div>
        </div>

        <div className="text-right text-[12px] text-muted-foreground">
          <div>Рекорд: <strong className="text-foreground font-semibold">{longest}</strong></div>
          <div>Всего: <strong className="text-foreground font-semibold">{total}</strong></div>
        </div>
      </div>

      {/* Milestones grid */}
      <div className="space-y-1.5 pt-1">
        <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-1">
          <Award className="h-3.5 w-3.5" />
          <span>Достижения</span>
        </div>

        <div className="grid grid-cols-4 gap-2 pt-0.5">
          {MILESTONES.map((m) => {
            const achieved = longest >= m.days
            return (
              <div
                key={m.days}
                data-testid={`milestone-badge-${m.days}`}
                data-achieved={achieved}
                className={`rounded-xl border p-2 text-center transition ${
                  achieved
                    ? "border-[#b07b36]/40 bg-[#fbf1de] dark:bg-[#2d261a] text-[#b07b36] dark:text-[#d49a4f]"
                    : "border-border/40 bg-muted/20 text-muted-foreground/50 opacity-60"
                }`}
              >
                <div className="text-[14px] font-bold leading-none mb-1">
                  {achieved ? "🏆" : "🔒"}
                </div>
                <div className="text-[10.5px] font-semibold truncate">{m.label}</div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
// END_BLOCK: CHECKIN_STATS_CARD_COMPONENT

function pluralDays(n: number): string {
  const abs = Math.abs(n) % 100
  const last = abs % 10
  if (abs >= 11 && abs <= 19) return "дней"
  if (last === 1) return "день"
  if (last >= 2 && last <= 4) return "дня"
  return "дней"
}
