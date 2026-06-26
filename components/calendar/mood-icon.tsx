"use client"

import { cn } from "@/lib/utils"
import type { DayStatus } from "@/lib/calendar"

/**
 * Иконка «тона дня» — нейтральные эмодзи, понятные всем.
 *
 *   supportive  → ⭐ звезда    — отличный день
 *   even        → ◐ полукруг   — ровный, обычный день
 *   tense       → ⚠ внимание   — напряжённый, осторожно
 *
 * Цвет круга-плашки соответствует тону. Нейтральная палитра.
 * Без хинтов и тултипов — всё видно сразу.
 */

type Props = {
  status: DayStatus
  className?: string
}

const STATUS_VISUAL: Record<DayStatus, { emoji: string; color: string; bg: string }> = {
  supportive: { emoji: "⭐", color: "oklch(0.68 0.13 85)", bg: "oklch(0.68 0.13 85 / 0.16)" },
  even: { emoji: "◐", color: "oklch(0.55 0.04 295)", bg: "oklch(0.55 0.04 295 / 0.10)" },
  tense: { emoji: "⚠️", color: "oklch(0.62 0.12 27)", bg: "oklch(0.62 0.12 27 / 0.12)" },
}

export function MoodIcon({ status, className }: Props) {
  const visual = STATUS_VISUAL[status] ?? STATUS_VISUAL.even
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex items-center justify-center rounded-full",
        className,
      )}
      style={{ background: visual.bg }}
    >
      <span
        className="leading-none"
        style={{ fontSize: "0.875em" }}
      >
        {visual.emoji}
      </span>
    </span>
  )
}
