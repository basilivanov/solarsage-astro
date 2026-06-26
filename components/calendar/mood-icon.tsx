"use client"

import { cn } from "@/lib/utils"
import type { DayStatus } from "@/lib/calendar"

/**
 * Иконка «тона дня» — понятные с одного взгляда эмодзи для девочек.
 *
 *   supportive  → 🌟 звёздочка   — крутой день, огонь
 *   even        → 🌸 цветок      — норм, ровный день
 *   tense       → 🌧️ дождик      — так себе, напряжённый
 *
 * Цвет круга-плашки соответствует тону. Мягкие пастельные тона.
 * Без хинтов и тултипов — всё видно сразу.
 */

type Props = {
  status: DayStatus
  className?: string
}

const STATUS_VISUAL: Record<DayStatus, { emoji: string; color: string; bg: string }> = {
  supportive: { emoji: "🌟", color: "oklch(0.68 0.13 85)", bg: "oklch(0.68 0.13 85 / 0.18)" },
  even: { emoji: "🌸", color: "oklch(0.70 0.12 350)", bg: "oklch(0.70 0.12 350 / 0.14)" },
  tense: { emoji: "🌧️", color: "oklch(0.60 0.06 230)", bg: "oklch(0.60 0.06 230 / 0.14)" },
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
