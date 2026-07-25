
// ############################################################################
// AI_HEADER: MODULE_CALENDAR_MOOD_ICON
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################
// START_MODULE_CONTRACT: M-COMPONENTS-CALENDAR-MOOD-ICON
// purpose: Render day status icon for calendar day cells (supportive, even, tense).
// owns:
//   - components/calendar/mood-icon.tsx
// inputs: status (DayStatus), className
// outputs: MoodIcon React component
// dependencies: lib/utils, lib/calendar
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-COMPONENTS-CALENDAR-MOOD-ICON

// START_MODULE_MAP: M-COMPONENTS-CALENDAR-MOOD-ICON
// public_entrypoints:
//   - MoodIcon
// semantic_blocks:
//   - MOOD_ICON_COMPONENT: calendar day mood icon component
// owned_tests:
//   - __tests__/components/CalendarScreen.test.tsx
// END_MODULE_MAP: M-COMPONENTS-CALENDAR-MOOD-ICON
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

// START_BLOCK: MOOD_ICON_COMPONENT
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
// END_BLOCK: MOOD_ICON_COMPONENT
