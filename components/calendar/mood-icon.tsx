
// ############################################################################
// AI_HEADER: MODULE_CALENDAR_MOOD_ICON
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Module: mood-icon.tsx
// owns:
//   - components/calendar/mood-icon.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-COMPONENTS-CALENDAR-MOOD-ICON
// wave: W-2.7
// purpose: MoodIcon component (migrated from legacy)

import { cn } from "@/lib/utils"
import type { DayStatus } from "@/lib/calendar"

/**
 * Иконка «тона дня» — нейтральные эмодзи, понятные всем.
 *
 *   supportive  → ⭐ звезда    — отличный день
 *   even        → ◐ полукруг   — ровный, обычный день
 *   tense       → ⚠️ внимание   — напряжённый, осторожно
 *
 * Цвет круга-плашки соответствует тону. Нейтральная палитра.
 * Без хинтов и тултипов — всё видно сразу.
 */
type Props = {
  status: DayStatus
  className?: string
  strokeWidth?: number // Kept for compatibility
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
