"use client"

import { cn } from "@/lib/utils"
import type { DayStatus } from "@/lib/calendar"

/**
 * Иконка «тона дня» — красивые эмодзи в цветном круге.
 *
 *   tense       → 🔥 огонь (напряжённый, горячий)
 *   even        → 🌙 луна (ровный, спокойный)
 *   supportive  → ✨ блёстки (поддерживающий, лёгкий)
 *
 * Цвет круга соответствует тону. Для девочек — мягкие пастельные тона.
 */

type Props = {
  status: DayStatus
  className?: string
}

const STATUS_VISUAL: Record<DayStatus, { emoji: string; color: string; bg: string }> = {
  tense: { emoji: "🔥", color: "oklch(0.65 0.15 27)", bg: "oklch(0.65 0.15 27 / 0.14)" },
  even: { emoji: "🌙", color: "oklch(0.60 0.06 295)", bg: "oklch(0.60 0.06 295 / 0.12)" },
  supportive: { emoji: "✨", color: "oklch(0.68 0.13 85)", bg: "oklch(0.68 0.13 85 / 0.16)" },
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
